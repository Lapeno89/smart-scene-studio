"""Authenticated scene-management commands for the Home Assistant WebSocket API."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import probatio
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DATA_PRESETS, DATA_REPOSITORY, DATA_SCENE_MANAGER, DOMAIN
from .models import validate_scene
from .repository import SceneRepository, UnsupportedStorageVersion
from .scene_bundle import (
    MAX_BUNDLE_BYTES,
    create_export_bundle,
    import_report,
    plan_scene_import,
)

_COMMAND_PREFIX = f"{DOMAIN}/scene"
_CREATE_FIELDS = {
    "name",
    "category",
    "favorite",
    "palette",
    "targets",
    "brightness_pct",
    "transition",
}
_UPDATE_FIELDS = _CREATE_FIELDS
_MAX_COMMAND_BYTES = 64 * 1024
_IMPORT_FIELDS = {"bundle", "dry_run", "target_mappings"}


def async_setup(hass: HomeAssistant) -> None:
    """Register the scene API once during integration setup."""
    websocket_api.async_register_command(hass, websocket_list_scenes)
    websocket_api.async_register_command(hass, websocket_get_scene)
    websocket_api.async_register_command(hass, websocket_create_scene)
    websocket_api.async_register_command(hass, websocket_update_scene)
    websocket_api.async_register_command(hass, websocket_duplicate_scene)
    websocket_api.async_register_command(hass, websocket_delete_scene)
    websocket_api.async_register_command(hass, websocket_export_scenes)
    websocket_api.async_register_command(hass, websocket_import_scenes)


def _get_runtime(
    hass: HomeAssistant,
) -> tuple[SceneRepository, tuple[dict[str, Any], ...], Any]:
    """Get the single configured scene repository and immutable presets."""
    domain_data = hass.data.get(DOMAIN, {})
    presets = domain_data.get(DATA_PRESETS)
    for value in domain_data.values():
        if isinstance(value, dict) and isinstance(value.get(DATA_REPOSITORY), SceneRepository):
            if presets is None or DATA_SCENE_MANAGER not in value:
                raise HomeAssistantError("Built-in scene data is unavailable")
            return value[DATA_REPOSITORY], tuple(presets), value[DATA_SCENE_MANAGER]
    raise HomeAssistantError("Smart Scene Studio is not configured")


async def _async_sync_entities(
    manager: Any,
    repository: SceneRepository,
    presets: tuple[dict[str, Any], ...],
) -> None:
    """Reconcile the live scene platform during initial setup."""
    await manager.async_sync((*presets, *repository.scenes))


async def _async_mutate_and_sync(
    manager: Any,
    repository: SceneRepository,
    presets: tuple[dict[str, Any], ...],
    mutation: Callable[[], Awaitable[Any]],
) -> tuple[Any, bool]:
    """Persist a mutation and reconcile the latest snapshot under one manager lock."""
    return await manager.async_mutate_and_sync(mutation, lambda: (*presets, *repository.scenes))


async def _async_reconcile_if_pending(
    manager: Any,
    repository: SceneRepository,
    presets: tuple[dict[str, Any], ...],
) -> bool:
    """Retry a failed platform reconciliation without changing persisted scenes."""
    return await manager.async_reconcile_if_pending(lambda: (*presets, *repository.scenes))


def _entity_sync_status(synchronized: bool) -> dict[str, Any]:
    """Explain whether the persisted scene is reflected in native HA entities."""
    if synchronized:
        return {"status": "complete"}
    return {
        "status": "pending",
        "message": (
            "The scene change is saved. Native entity synchronization failed; "
            "a later scene API request will retry it."
        ),
    }


def _api_scene(scene: dict[str, Any], provenance: str) -> dict[str, Any]:
    """Return a detached API representation with explicit source provenance."""
    return {**deepcopy(scene), "provenance": provenance}


def _reject_extra_fields(msg: dict[str, Any], allowed: set[str]) -> None:
    extra = msg.keys() - {"id", "type"} - allowed
    if extra:
        raise HomeAssistantError(f"Unsupported command fields: {', '.join(sorted(extra))}")


def _scene_payload(value: Any, allowed_fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HomeAssistantError("Scene must be an object")
    if extra := value.keys() - allowed_fields:
        raise HomeAssistantError(f"Unsupported scene fields: {', '.join(sorted(extra))}")
    if len(json.dumps(value, separators=(",", ":"))) > _MAX_COMMAND_BYTES:
        raise HomeAssistantError("Scene payload exceeds the 64 KiB limit")
    if "name" not in value or "palette" not in value:
        raise HomeAssistantError("Scene name and palette are required")
    return value


def _find_scene(
    scene_id: str,
    repository: SceneRepository,
    presets: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any] | None, str | None]:
    if user_scene := next((scene for scene in repository.scenes if scene["id"] == scene_id), None):
        return user_scene, "user"
    if builtin := next((scene for scene in presets if scene["id"] == scene_id), None):
        return builtin, "builtin"
    return None, None


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@websocket_api.ws_require_user()
@websocket_api.async_response
@websocket_api.websocket_command({probatio.Required("type"): f"{_COMMAND_PREFIX}/list"})
async def websocket_list_scenes(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return immutable built-ins and the configured user's saved scenes."""
    _reject_extra_fields(msg, set())
    repository, presets, manager = _get_runtime(hass)
    synchronized = await _async_reconcile_if_pending(manager, repository, presets)
    scenes = [_api_scene(scene, "builtin") for scene in presets]
    scenes.extend(_api_scene(scene, "user") for scene in repository.scenes)
    connection.send_result(
        msg["id"],
        {
            "scenes": scenes,
            "entity_sync": _entity_sync_status(synchronized),
        },
    )


@websocket_api.ws_require_user()
@websocket_api.async_response
@websocket_api.websocket_command(
    {
        probatio.Required("type"): f"{_COMMAND_PREFIX}/get",
        probatio.Required("scene_id"): str,
    }
)
async def websocket_get_scene(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get one built-in or user-authored scene by immutable UUID."""
    _reject_extra_fields(msg, {"scene_id"})
    repository, presets, manager = _get_runtime(hass)
    synchronized = await _async_reconcile_if_pending(manager, repository, presets)
    scene, provenance = _find_scene(msg["scene_id"], repository, presets)
    if scene is None or provenance is None:
        raise HomeAssistantError("Scene not found")
    connection.send_result(
        msg["id"],
        {
            "scene": _api_scene(scene, provenance),
            "entity_sync": _entity_sync_status(synchronized),
        },
    )


@websocket_api.require_admin
@websocket_api.async_response
@websocket_api.websocket_command(
    {
        probatio.Required("type"): f"{_COMMAND_PREFIX}/create",
        probatio.Required("scene"): dict,
    }
)
async def websocket_create_scene(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Create a user scene with a server-generated immutable UUID."""
    _reject_extra_fields(msg, {"scene"})
    payload = _scene_payload(msg["scene"], _CREATE_FIELDS)
    repository, presets, manager = _get_runtime(hass)
    scene = validate_scene(
        {
            **payload,
            "id": str(uuid4()),
            "kind": "static",
            "created_at": _now(),
            "updated_at": _now(),
        }
    )
    try:
        saved, synchronized = await _async_mutate_and_sync(
            manager,
            repository,
            presets,
            lambda: repository.async_save_scene(scene),
        )
    except (ValueError, UnsupportedStorageVersion) as err:
        raise HomeAssistantError(str(err)) from err
    connection.send_result(
        msg["id"],
        {
            "scene": _api_scene(saved, "user"),
            "entity_sync": _entity_sync_status(synchronized),
        },
    )


@websocket_api.require_admin
@websocket_api.async_response
@websocket_api.websocket_command(
    {
        probatio.Required("type"): f"{_COMMAND_PREFIX}/update",
        probatio.Required("scene_id"): str,
        probatio.Required("updates"): dict,
    }
)
async def websocket_update_scene(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Update mutable user fields without allowing ID or provenance changes."""
    _reject_extra_fields(msg, {"scene_id", "updates"})
    updates = msg["updates"]
    if not isinstance(updates, dict) or not updates:
        raise HomeAssistantError("Updates must be a non-empty object")
    if extra := updates.keys() - _UPDATE_FIELDS:
        raise HomeAssistantError(f"Unsupported update fields: {', '.join(sorted(extra))}")
    repository, presets, manager = _get_runtime(hass)
    scene, provenance = _find_scene(msg["scene_id"], repository, presets)
    if scene is None:
        raise HomeAssistantError("Scene not found")
    if provenance != "user":
        raise HomeAssistantError("Built-in scenes are read-only; duplicate one to edit it")
    try:
        updated, synchronized = await _async_mutate_and_sync(
            manager,
            repository,
            presets,
            lambda: repository.async_update_scene(
                msg["scene_id"], {**updates, "updated_at": _now()}
            ),
        )
    except (KeyError, ValueError, UnsupportedStorageVersion) as err:
        raise HomeAssistantError(str(err)) from err
    connection.send_result(
        msg["id"],
        {
            "scene": _api_scene(updated, "user"),
            "entity_sync": _entity_sync_status(synchronized),
        },
    )


@websocket_api.require_admin
@websocket_api.async_response
@websocket_api.websocket_command(
    {
        probatio.Required("type"): f"{_COMMAND_PREFIX}/duplicate",
        probatio.Required("scene_id"): str,
        probatio.Optional("name"): str,
    }
)
async def websocket_duplicate_scene(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Clone a built-in or user scene as a new user-owned scene."""
    _reject_extra_fields(msg, {"scene_id", "name"})
    repository, presets, manager = _get_runtime(hass)
    source, _ = _find_scene(msg["scene_id"], repository, presets)
    if source is None:
        raise HomeAssistantError("Scene not found")
    created_at = _now()
    payload = {
        key: deepcopy(value)
        for key, value in source.items()
        if key in _CREATE_FIELDS and key != "kind"
    }
    payload.update(
        {
            "id": str(uuid4()),
            "kind": "static",
            "name": msg.get("name", f"{source['name']} (copy)"),
            "created_at": created_at,
            "updated_at": created_at,
        }
    )
    try:
        duplicate, synchronized = await _async_mutate_and_sync(
            manager,
            repository,
            presets,
            lambda: repository.async_save_scene(validate_scene(payload)),
        )
    except (ValueError, UnsupportedStorageVersion) as err:
        raise HomeAssistantError(str(err)) from err
    connection.send_result(
        msg["id"],
        {
            "scene": _api_scene(duplicate, "user"),
            "entity_sync": _entity_sync_status(synchronized),
        },
    )


@websocket_api.require_admin
@websocket_api.async_response
@websocket_api.websocket_command(
    {
        probatio.Required("type"): f"{_COMMAND_PREFIX}/delete",
        probatio.Required("scene_id"): str,
    }
)
async def websocket_delete_scene(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete a user scene; built-in presets are immutable."""
    _reject_extra_fields(msg, {"scene_id"})
    repository, presets, manager = _get_runtime(hass)
    scene, provenance = _find_scene(msg["scene_id"], repository, presets)
    if scene is None:
        raise HomeAssistantError("Scene not found")
    if provenance != "user":
        raise HomeAssistantError("Built-in scenes are read-only")
    try:
        _, synchronized = await _async_mutate_and_sync(
            manager,
            repository,
            presets,
            lambda: repository.async_delete_scene(msg["scene_id"]),
        )
    except (KeyError, UnsupportedStorageVersion) as err:
        raise HomeAssistantError(str(err)) from err
    connection.send_result(
        msg["id"],
        {
            "deleted": msg["scene_id"],
            "entity_sync": _entity_sync_status(synchronized),
        },
    )


@websocket_api.ws_require_user()
@websocket_api.async_response
@websocket_api.websocket_command(
    {
        probatio.Required("type"): f"{_COMMAND_PREFIX}/export",
        probatio.Optional("scene_ids"): list,
    }
)
async def websocket_export_scenes(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Export selected or all scenes as a versioned, secret-free JSON bundle."""
    _reject_extra_fields(msg, {"scene_ids"})
    scene_ids = msg.get("scene_ids")
    if scene_ids is not None and (
        not isinstance(scene_ids, list) or any(not isinstance(item, str) for item in scene_ids)
    ):
        raise HomeAssistantError("scene_ids must be a list of strings")
    repository, presets, _ = _get_runtime(hass)
    try:
        bundle = create_export_bundle(presets, repository.scenes, scene_ids)
    except ValueError as err:
        raise HomeAssistantError(str(err)) from err
    if len(json.dumps(bundle, separators=(",", ":")).encode("utf-8")) > MAX_BUNDLE_BYTES:
        raise HomeAssistantError("Scene bundle exceeds the 1 MiB limit")
    connection.send_result(msg["id"], {"bundle": bundle})


@websocket_api.require_admin
@websocket_api.async_response
@websocket_api.websocket_command(
    {
        probatio.Required("type"): f"{_COMMAND_PREFIX}/import",
        probatio.Required("bundle"): dict,
        probatio.Required("dry_run"): bool,
        probatio.Optional("target_mappings"): dict,
    }
)
async def websocket_import_scenes(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Preview or atomically import a validated, portable scene bundle."""
    _reject_extra_fields(msg, _IMPORT_FIELDS)
    try:
        encoded = json.dumps(msg["bundle"], separators=(",", ":"), ensure_ascii=True)
    except (TypeError, ValueError) as err:
        raise HomeAssistantError("Scene bundle must contain JSON-compatible values") from err
    if len(encoded.encode("utf-8")) > MAX_BUNDLE_BYTES:
        raise HomeAssistantError("Scene bundle exceeds the 1 MiB limit")

    repository, presets, manager = _get_runtime(hass)
    mappings = msg.get("target_mappings", {})
    if msg["dry_run"]:
        try:
            plan = plan_scene_import(msg["bundle"], mappings, repository.scenes, list(presets))
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        connection.send_result(msg["id"], {"report": import_report(plan, dry_run=True)})
        return

    async def mutation() -> dict[str, Any]:
        plan = plan_scene_import(msg["bundle"], mappings, repository.scenes, list(presets))
        # The manager lock serializes planning, batch persistence and entity reconciliation.
        await repository.async_save_scenes(plan["scenes"])
        return plan

    try:
        result, synchronized = await _async_mutate_and_sync(
            manager, repository, presets, mutation
        )
    except (OSError, ValueError, UnsupportedStorageVersion) as err:
        raise HomeAssistantError(str(err)) from err
    report = import_report(result, dry_run=False)
    report["entity_sync"] = _entity_sync_status(synchronized)
    connection.send_result(msg["id"], {"report": report})


async def async_load_presets(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Load and validate the original packaged read-only preset collection."""
    path = Path(__file__).with_name("presets.json")
    preset_text = await hass.async_add_executor_job(path.read_text, "utf-8")
    return [validate_scene(item) for item in json.loads(preset_text)]
