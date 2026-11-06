"""Authenticated scene CRUD API tests; the websocket server is test-only."""

import asyncio
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from homeassistant.components.light import ColorMode
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.smart_scene_studio.const import DATA_REPOSITORY, DATA_SCENE_ENTITIES, DOMAIN
from custom_components.smart_scene_studio.repository import SceneRepository
from tests.test_integration import add_entry

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

BUILTIN_ID = "b88ea8a1-0db4-4df5-9e91-4d93a3d30001"
CREATE_SCENE = {
    "name": "Reading",
    "palette": ["#112233", "#445566"],
    "targets": [],
}


async def request(client, payload: dict):
    await client.send_json_auto_id(payload)
    return await client.receive_json()


async def test_scene_crud_and_builtin_immutability(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    """Exercise create, list, get, update, duplicate and delete commands."""
    await add_entry(hass)
    client = await hass_ws_client(hass)

    created_response = await request(
        client, {"type": f"{DOMAIN}/scene/create", "scene": CREATE_SCENE}
    )
    assert created_response["success"]
    created = created_response["result"]["scene"]
    UUID(created["id"])
    assert created["provenance"] == "user"
    created_id = created["id"]
    created_at = created["created_at"]

    listing = await request(client, {"type": f"{DOMAIN}/scene/list"})
    assert listing["success"]
    listed = {scene["id"]: scene for scene in listing["result"]["scenes"]}
    assert listed[BUILTIN_ID]["provenance"] == "builtin"
    assert listed[created_id]["name"] == "Reading"

    fetched = await request(client, {"type": f"{DOMAIN}/scene/get", "scene_id": created_id})
    assert fetched["result"]["scene"]["id"] == created_id

    updated_response = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/update",
            "scene_id": created_id,
            "updates": {"name": "Reading corner", "favorite": True},
        },
    )
    updated = updated_response["result"]["scene"]
    assert updated["id"] == created_id
    assert updated["created_at"] == created_at
    assert updated["name"] == "Reading corner"

    duplicate_response = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/duplicate",
            "scene_id": BUILTIN_ID,
            "name": "Amber copy",
        },
    )
    duplicate = duplicate_response["result"]["scene"]
    assert duplicate["id"] != BUILTIN_ID
    assert duplicate["name"] == "Amber copy"
    assert duplicate["provenance"] == "user"

    builtin_update = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/update",
            "scene_id": BUILTIN_ID,
            "updates": {"name": "Changed"},
        },
    )
    assert not builtin_update["success"]
    builtin_delete = await request(
        client, {"type": f"{DOMAIN}/scene/delete", "scene_id": BUILTIN_ID}
    )
    assert not builtin_delete["success"]

    deleted = await request(client, {"type": f"{DOMAIN}/scene/delete", "scene_id": created_id})
    assert deleted["success"]
    missing = await request(client, {"type": f"{DOMAIN}/scene/get", "scene_id": created_id})
    assert not missing["success"]


async def test_native_scene_entities_track_crud_without_reload(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    """Create, rename, unassign, reassign and delete native scenes live."""
    await add_entry(hass)
    client = await hass_ws_client(hass)
    create = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/create",
            "scene": {
                **CREATE_SCENE,
                "name": "Live scene",
                "targets": [{"entity_id": "light.test_lamp"}],
            },
        },
    )
    assert create["success"]
    scene_id = create["result"]["scene"]["id"]
    entity = hass.data[DOMAIN][DATA_SCENE_ENTITIES][scene_id]
    entity_id = entity.entity_id
    assert entity.unique_id == scene_id
    assert hass.states.get(entity_id) is not None

    renamed = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/update",
            "scene_id": scene_id,
            "updates": {"name": "Renamed live scene"},
        },
    )
    assert renamed["success"]
    assert hass.data[DOMAIN][DATA_SCENE_ENTITIES][scene_id] is entity
    assert hass.states.get(entity_id).name == "Renamed live scene"
    assert hass.data[DOMAIN][DATA_SCENE_ENTITIES][scene_id].unique_id == scene_id

    unassigned = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/update",
            "scene_id": scene_id,
            "updates": {"targets": []},
        },
    )
    assert unassigned["success"]
    assert scene_id not in hass.data[DOMAIN][DATA_SCENE_ENTITIES]
    assert hass.states.get(entity_id) is None

    reassigned = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/update",
            "scene_id": scene_id,
            "updates": {"targets": [{"entity_id": "light.test_lamp"}]},
        },
    )
    assert reassigned["success"]
    restored = hass.data[DOMAIN][DATA_SCENE_ENTITIES][scene_id]
    assert restored.unique_id == scene_id
    assert restored.entity_id == entity_id
    assert hass.states.get(entity_id) is not None

    deleted = await request(client, {"type": f"{DOMAIN}/scene/delete", "scene_id": scene_id})
    assert deleted["success"]
    assert scene_id not in hass.data[DOMAIN][DATA_SCENE_ENTITIES]
    assert hass.states.get(entity_id) is None
    assert er.async_get(hass).async_get_entity_id("scene", DOMAIN, scene_id) is None


async def test_concurrent_api_updates_reconcile_the_final_saved_snapshot(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    monkeypatch,
) -> None:
    """Serialize scene persistence and HA synchronization as one mutation."""
    entry = await add_entry(hass)
    first_client = await hass_ws_client(hass)
    second_client = await hass_ws_client(hass)
    created = await request(
        first_client,
        {
            "type": f"{DOMAIN}/scene/create",
            "scene": {
                **CREATE_SCENE,
                "name": "Concurrency scene",
                "targets": [{"entity_id": "light.initial"}],
            },
        },
    )
    scene_id = created["result"]["scene"]["id"]
    repository = hass.data[DOMAIN][entry.entry_id]["repository"]
    manager = hass.data[DOMAIN][entry.entry_id]["scene_manager"]
    original_sync = manager._async_sync_locked
    first_sync_entered = asyncio.Event()
    release_first_sync = asyncio.Event()
    sync_calls = 0

    async def pause_first_sync(definitions) -> None:
        nonlocal sync_calls
        sync_calls += 1
        if sync_calls == 1:
            first_sync_entered.set()
            await release_first_sync.wait()
        await original_sync(definitions)

    monkeypatch.setattr(manager, "_async_sync_locked", pause_first_sync)
    first_update = asyncio.create_task(
        request(
            first_client,
            {
                "type": f"{DOMAIN}/scene/update",
                "scene_id": scene_id,
                "updates": {
                    "name": "First update",
                    "targets": [{"entity_id": "light.first"}],
                },
            },
        )
    )
    await first_sync_entered.wait()
    second_update = asyncio.create_task(
        request(
            second_client,
            {
                "type": f"{DOMAIN}/scene/update",
                "scene_id": scene_id,
                "updates": {
                    "name": "Final update",
                    "targets": [{"entity_id": "light.final"}],
                },
            },
        )
    )
    try:
        await asyncio.sleep(0)
        assert repository.scenes[0]["name"] == "First update"
    finally:
        release_first_sync.set()

    first_response, second_response = await asyncio.gather(first_update, second_update)
    assert first_response["success"]
    assert second_response["success"]
    persisted = repository.scenes[0]
    reloaded_repository = SceneRepository(hass)
    await reloaded_repository.async_load()
    stored = reloaded_repository.scenes[0]
    entity = hass.data[DOMAIN][DATA_SCENE_ENTITIES][scene_id]
    assert stored["name"] == "Final update"
    assert stored["targets"] == [
        {"entity_id": "light.final", "enabled": True, "color_index": 0, "state": "on"}
    ]
    assert persisted["name"] == "Final update"
    assert persisted["targets"][0]["entity_id"] == "light.final"
    assert entity._definition["name"] == persisted["name"]
    assert entity._definition["targets"] == persisted["targets"]
    assert hass.states.get(entity.entity_id).name == persisted["name"]


async def test_platform_sync_failure_is_reported_as_pending_and_retried(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    monkeypatch,
) -> None:
    """A platform failure does not undo saved data and the next read retries sync."""
    entry = await add_entry(hass)
    client = await hass_ws_client(hass)
    repository = hass.data[DOMAIN][entry.entry_id]["repository"]
    manager = hass.data[DOMAIN][entry.entry_id]["scene_manager"]
    platform = manager._platform
    original_add_entities = platform.async_add_entities
    fail_once = True

    async def fail_first_add(entities, *args, **kwargs) -> None:
        nonlocal fail_once
        if fail_once:
            # HA logs and absorbs per-entity add errors; emulate no registration.
            fail_once = False
            return
        await original_add_entities(entities, *args, **kwargs)

    monkeypatch.setattr(platform, "async_add_entities", fail_first_add)
    response = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/create",
            "scene": {
                **CREATE_SCENE,
                "name": "Saved while platform is unavailable",
                "targets": [{"entity_id": "light.test_lamp"}],
            },
        },
    )

    assert response["success"]
    scene = response["result"]["scene"]
    assert response["result"]["entity_sync"]["status"] == "pending"
    assert "saved" in response["result"]["entity_sync"]["message"]
    assert repository.scenes[0]["id"] == scene["id"]
    assert manager.sync_pending
    assert scene["id"] not in manager.entities

    retried = await request(client, {"type": f"{DOMAIN}/scene/list"})
    assert retried["success"]
    assert retried["result"]["entity_sync"]["status"] == "complete"
    assert not manager.sync_pending
    assert scene["id"] in manager.entities
    assert hass.states.get(manager.entities[scene["id"]].entity_id) is not None


async def test_native_scene_enforces_mapped_light_control_permission(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    hass_admin_user,
    monkeypatch,
) -> None:
    """A non-admin cannot activate a scene targeting a light they cannot control."""
    await add_entry(hass)
    client = await hass_ws_client(hass)
    create = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/create",
            "scene": {
                **CREATE_SCENE,
                "name": "Restricted target",
                "targets": [{"entity_id": "light.test_lamp"}],
            },
        },
    )
    scene_id = create["result"]["scene"]["id"]
    scene_entity = hass.data[DOMAIN][DATA_SCENE_ENTITIES][scene_id]
    hass_admin_user.groups = []
    monkeypatch.setattr(
        hass_admin_user.permissions,
        "check_entity",
        lambda entity_id, permission: False,
    )
    scene_entity.async_set_context(Context(user_id=hass_admin_user.id))
    light_call = AsyncMock()
    hass.services.async_register("light", "turn_on", light_call)
    hass.states.async_set("light.test_lamp", "off", {"supported_color_modes": [ColorMode.RGB]})

    with pytest.raises(Unauthorized):
        await scene_entity.async_activate()

    light_call.assert_not_awaited()


async def test_scene_crud_requires_admin_for_mutations(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    hass_admin_user,
) -> None:
    """Authenticated non-admin users can read scenes but cannot mutate them."""
    await add_entry(hass)
    hass_admin_user.groups = []
    client = await hass_ws_client(hass)

    listing = await request(client, {"type": f"{DOMAIN}/scene/list"})
    assert listing["success"]
    created = await request(client, {"type": f"{DOMAIN}/scene/create", "scene": CREATE_SCENE})
    assert not created["success"]
    assert created["error"]["code"] == "unauthorized"


async def test_scene_api_rejects_unknown_fields_and_invalid_models(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    """Reject client-chosen identity, unsupported fields and malformed palettes."""
    await add_entry(hass)
    client = await hass_ws_client(hass)

    bad_id = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/create",
            "scene": {**CREATE_SCENE, "id": BUILTIN_ID},
        },
    )
    assert not bad_id["success"]

    unknown = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/create",
            "scene": {**CREATE_SCENE, "secret": "ignored?"},
        },
    )
    assert not unknown["success"]

    invalid_palette = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/create",
            "scene": {**CREATE_SCENE, "palette": ["red"]},
        },
    )
    assert not invalid_palette["success"]

    invalid_target = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/create",
            "scene": {
                **CREATE_SCENE,
                "targets": [{"entity_id": "light.test", "unexpected": True}],
            },
        },
    )
    assert not invalid_target["success"]


async def test_scene_api_does_not_report_success_after_store_failure(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, monkeypatch
) -> None:
    """A failed Store write returns an error and registers no transient entity."""
    entry = await add_entry(hass)
    repository = hass.data[DOMAIN][entry.entry_id]["repository"]
    monkeypatch.setattr(
        repository._store,
        "async_save",
        AsyncMock(side_effect=OSError("simulated Store failure")),
    )
    client = await hass_ws_client(hass)

    response = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/create",
            "scene": {
                **CREATE_SCENE,
                "name": "Not persisted",
                "targets": [{"entity_id": "light.test_lamp"}],
            },
        },
    )

    assert not response["success"]
    assert repository.scenes == ()
    assert hass.data[DOMAIN][DATA_SCENE_ENTITIES] == {}


async def test_scene_json_export_and_import_preview_and_commit(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    """Export uses an allow-listed bundle; preview is read-only and commit is idempotent."""
    entry = await add_entry(hass)
    client = await hass_ws_client(hass)
    created = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/create",
            "scene": {
                **CREATE_SCENE,
                "name": "Portable",
                "targets": [{"entity_id": "light.source"}],
            },
        },
    )
    scene_id = created["result"]["scene"]["id"]
    exported = await request(client, {"type": f"{DOMAIN}/scene/export"})
    assert exported["success"]
    exported_bundle = exported["result"]["bundle"]
    assert exported_bundle["format"] == f"{DOMAIN}.scene_bundle"
    assert "provenance" in next(
        item for item in exported_bundle["scenes"] if item["id"] == scene_id
    )

    source = next(item for item in exported_bundle["scenes"] if item["id"] == scene_id)
    source_bundle = {
        "format": exported_bundle["format"],
        "version": exported_bundle["version"],
        "scenes": [source],
    }
    import_message = {
        "type": f"{DOMAIN}/scene/import",
        "bundle": source_bundle,
        "dry_run": True,
        "target_mappings": {"light.source": "light.destination"},
    }
    preview = await request(client, import_message)
    assert preview["success"]
    assert preview["result"]["report"]["dry_run"] is True
    assert preview["result"]["report"]["imported_count"] == 1
    repository = hass.data[DOMAIN][entry.entry_id][DATA_REPOSITORY]
    assert len(repository.scenes) == 1

    imported = await request(client, {**import_message, "dry_run": False})
    assert imported["success"]
    report = imported["result"]["report"]
    assert report["dry_run"] is False
    assert report["imported_count"] == 1
    assert report["entity_sync"]["status"] == "complete"
    assert len(repository.scenes) == 2
    assert next(scene for scene in repository.scenes if scene["id"] != scene_id)["targets"][0][
        "entity_id"
    ] == "light.destination"

    repeated = await request(client, {**import_message, "dry_run": False})
    assert repeated["success"]
    assert repeated["result"]["report"]["imported_count"] == 0
    assert repeated["result"]["report"]["skipped_count"] == 1
    assert len(repository.scenes) == 2


async def test_scene_json_import_requires_admin_but_export_is_available_to_users(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    hass_admin_user,
) -> None:
    """Non-admin authenticated users may export, but import requires administration."""
    await add_entry(hass)
    hass_admin_user.groups = []
    client = await hass_ws_client(hass)

    exported = await request(client, {"type": f"{DOMAIN}/scene/export"})
    assert exported["success"]
    denied = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/import",
            "bundle": {
                "format": f"{DOMAIN}.scene_bundle",
                "version": 1,
                "scenes": [],
            },
            "dry_run": True,
        },
    )
    assert not denied["success"]
    assert denied["error"]["code"] == "unauthorized"


async def test_scene_json_import_store_failure_is_atomic(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, monkeypatch
) -> None:
    """A failed batch Store write publishes no imported scenes or native entities."""
    entry = await add_entry(hass)
    repository = hass.data[DOMAIN][entry.entry_id]["repository"]
    monkeypatch.setattr(
        repository._store,
        "async_save",
        AsyncMock(side_effect=OSError("simulated Store failure")),
    )
    client = await hass_ws_client(hass)
    response = await request(
        client,
        {
            "type": f"{DOMAIN}/scene/import",
            "dry_run": False,
            "bundle": {
                "format": f"{DOMAIN}.scene_bundle",
                "version": 1,
                "scenes": [{
                    "id": "f3481166-f3fb-4a0b-87bc-12462c965e17",
                    "name": "Atomic import",
                    "kind": "static",
                    "palette": ["#112233", "#445566"],
                    "targets": [{"entity_id": "light.source"}],
                }],
            },
            "target_mappings": {"light.source": "light.destination"},
        },
    )

    assert not response["success"]
    assert repository.scenes == ()
    assert hass.data[DOMAIN][DATA_SCENE_ENTITIES] == {}


async def test_scene_json_import_preview_reports_capacity_and_commit_is_atomic(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    """Preview warns about the 500-scene limit and commit leaves the Store unchanged."""
    entry = await add_entry(hass)
    repository = hass.data[DOMAIN][entry.entry_id][DATA_REPOSITORY]
    existing = [
        {
            **CREATE_SCENE,
            "id": str(uuid4()),
            "name": f"Existing {index}",
        }
        for index in range(499)
    ]
    await repository.async_save_scenes(existing)
    incoming = [
        {
            "id": str(uuid4()),
            "name": f"Incoming {index}",
            "kind": "static",
            "palette": ["#112233", "#445566"],
            "targets": [],
        }
        for index in range(2)
    ]
    command = {
        "type": f"{DOMAIN}/scene/import",
        "bundle": {
            "format": f"{DOMAIN}.scene_bundle",
            "version": 1,
            "scenes": incoming,
        },
        "dry_run": True,
    }
    client = await hass_ws_client(hass)

    preview = await request(client, command)

    assert preview["success"]
    report = preview["result"]["report"]
    assert report["imported_count"] == 2
    assert report["capacity"]["can_commit"] is False
    assert report["capacity"]["current_scene_count"] == 499
    assert report["capacity"]["proposed_scene_count"] == 501
    assert any("maximum of 500" in error for error in report["capacity"]["errors"])
    assert len(repository.scenes) == 499

    committed = await request(client, {**command, "dry_run": False})

    assert not committed["success"]
    assert "500 user scenes" in committed["error"]["message"]
    assert len(repository.scenes) == 499


async def test_scene_json_import_preview_reports_storage_size_limit(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    """Preview checks serialized Store bytes, not just the scene-count limit."""
    entry = await add_entry(hass)
    repository = hass.data[DOMAIN][entry.entry_id][DATA_REPOSITORY]

    def large_scene(name: str, scene_id: str) -> dict:
        targets = [
            {"entity_id": f"light.{index:03d}" + "x" * 246}
            for index in range(64)
        ]
        return {
            "id": scene_id,
            "name": name,
            "kind": "static",
            "palette": ["#112233", "#445566"],
            "targets": targets,
        }

    await repository.async_save_scenes(
        [large_scene(f"Stored {index}", str(uuid4())) for index in range(50)]
    )
    incoming = [
        large_scene(f"Incoming large scene {index}", str(uuid4()))
        for index in range(2)
    ]
    command = {
        "type": f"{DOMAIN}/scene/import",
        "bundle": {
            "format": f"{DOMAIN}.scene_bundle",
            "version": 1,
            "scenes": incoming,
        },
        "dry_run": True,
    }
    client = await hass_ws_client(hass)

    preview = await request(client, command)

    assert preview["success"]
    report = preview["result"]["report"]
    assert report["imported_count"] == 2
    assert report["capacity"]["can_commit"] is False
    assert any("1 MiB" in error for error in report["capacity"]["errors"])
    assert len(repository.scenes) == 50

    committed = await request(client, {**command, "dry_run": False})

    assert not committed["success"]
    assert "1 MiB" in committed["error"]["message"]
    assert len(repository.scenes) == 50


async def test_anonymous_websocket_cannot_access_scene_api(
    hass: HomeAssistant, aiohttp_client, socket_enabled: None
) -> None:
    """An anonymous socket cannot enter command phase or send scene commands."""
    from homeassistant.setup import async_setup_component

    await add_entry(hass)
    assert await async_setup_component(hass, "websocket_api", {})
    client = await aiohttp_client(hass.http.app)
    websocket = await client.ws_connect("/api/websocket")
    assert (await websocket.receive_json())["type"] == "auth_required"
    await websocket.close()
    await hass.async_block_till_done()


async def test_crud_scene_survives_integration_reload(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    """Persisted API-created scenes remain addressable after integration reload."""
    entry = await add_entry(hass)
    client = await hass_ws_client(hass)
    response = await request(client, {"type": f"{DOMAIN}/scene/create", "scene": CREATE_SCENE})
    scene_id = response["result"]["scene"]["id"]

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    reloaded = await request(client, {"type": f"{DOMAIN}/scene/get", "scene_id": scene_id})
    assert reloaded["success"]
    assert reloaded["result"]["scene"]["id"] == scene_id
