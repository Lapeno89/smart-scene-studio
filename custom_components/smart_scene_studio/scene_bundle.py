"""Portable versioned scene bundle validation and import planning."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from .const import DOMAIN
from .models import validate_scene

BUNDLE_FORMAT = f"{DOMAIN}.scene_bundle"
BUNDLE_VERSION = 1
MAX_BUNDLE_BYTES = 1_048_576
MAX_BUNDLE_SCENES = 503  # 500 user scenes plus the original built-in presets.
_LIGHT_ENTITY_ID = re.compile(r"^light\.[a-z0-9_]+$")
_SCENE_FIELD_ORDER = (
    "id",
    "name",
    "kind",
    "category",
    "favorite",
    "palette",
    "targets",
    "brightness_pct",
    "transition",
    "created_at",
    "updated_at",
)
_SCENE_FIELDS = set(_SCENE_FIELD_ORDER)
_BUNDLE_SCENE_FIELDS = _SCENE_FIELDS | {"provenance"}
_CONTENT_FIELDS = (
    "name",
    "kind",
    "category",
    "favorite",
    "palette",
    "targets",
    "brightness_pct",
    "transition",
)


def create_export_bundle(
    builtins: list[dict[str, Any]],
    user_scenes: tuple[dict[str, Any], ...],
    scene_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Create a secret-free, allow-listed JSON bundle."""
    available = [
        (_export_scene(scene), "builtin")
        for scene in builtins
    ] + [
        (_export_scene(scene), "user")
        for scene in user_scenes
    ]
    by_id = {scene["id"]: (scene, provenance) for scene, provenance in available}

    if scene_ids is None:
        selected = available
    else:
        if len(scene_ids) > MAX_BUNDLE_SCENES:
            raise ValueError(f"A maximum of {MAX_BUNDLE_SCENES} scenes can be exported")
        if any(not isinstance(scene_id, str) for scene_id in scene_ids):
            raise ValueError("scene_ids must contain strings")
        if len(set(scene_ids)) != len(scene_ids):
            raise ValueError("scene_ids cannot contain duplicates")
        missing = sorted(set(scene_ids) - by_id.keys())
        if missing:
            raise ValueError(f"Unknown scene IDs: {', '.join(missing)}")
        selected = [by_id[scene_id] for scene_id in scene_ids]

    bundle = {
        "format": BUNDLE_FORMAT,
        "version": BUNDLE_VERSION,
        "scenes": [
            {**scene, "provenance": provenance}
            for scene, provenance in selected
        ],
    }
    _validate_bundle_size(bundle)
    return bundle


def plan_scene_import(
    bundle: Any,
    target_mappings: Any,
    existing_scenes: tuple[dict[str, Any], ...],
    builtins: list[dict[str, Any]],
    *,
    now: str | None = None,
) -> dict[str, Any]:
    """Validate a bundle and return a deterministic, non-mutating import plan."""
    _validate_bundle_size({"bundle": bundle, "target_mappings": target_mappings})
    if not isinstance(bundle, dict):
        raise ValueError("Scene bundle must be an object")
    if extra := bundle.keys() - {"format", "version", "scenes"}:
        raise ValueError(f"Unsupported bundle fields: {', '.join(sorted(extra))}")
    if bundle.get("format") != BUNDLE_FORMAT:
        raise ValueError("Unsupported scene bundle format")
    version = bundle.get("version")
    if not isinstance(version, int) or isinstance(version, bool):
        raise ValueError("Scene bundle version must be an integer")
    if version != BUNDLE_VERSION:
        raise ValueError(f"Unsupported scene bundle version {version}")
    source_scenes = bundle.get("scenes")
    if not isinstance(source_scenes, list) or not source_scenes:
        raise ValueError("Scene bundle must contain a non-empty scenes list")
    if len(source_scenes) > MAX_BUNDLE_SCENES:
        raise ValueError(f"A maximum of {MAX_BUNDLE_SCENES} scenes can be imported")

    mappings = _validate_target_mappings(target_mappings)
    timestamp = now or datetime.now(UTC).isoformat(timespec="seconds")
    normalized: list[tuple[dict[str, Any], str, set[str]]] = []
    referenced_targets: set[str] = set()
    source_id_fingerprints: dict[str, str] = {}

    for source in source_scenes:
        if not isinstance(source, dict):
            raise ValueError("Each bundled scene must be an object")
        if extra := source.keys() - _BUNDLE_SCENE_FIELDS:
            raise ValueError(f"Unsupported bundled scene fields: {', '.join(sorted(extra))}")
        provenance = source.get("provenance", "user")
        if provenance not in ("builtin", "user"):
            raise ValueError("Bundled scene provenance must be builtin or user")
        candidate = validate_scene(
            {
                **{key: value for key, value in source.items() if key != "provenance"},
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        )
        source_target_ids = {target["entity_id"] for target in candidate["targets"]}
        referenced_targets.update(source_target_ids)
        unmapped_for_scene = source_target_ids - mappings.keys()
        remapped_targets = []
        destinations: set[str] = set()
        for target in candidate["targets"]:
            original_id = target["entity_id"]
            mapped_id = mappings.get(original_id)
            if mapped_id is None:
                remapped_targets.append({**target, "enabled": False})
                continue
            if mapped_id in destinations:
                raise ValueError(
                    f"Multiple targets in scene {candidate['id']} map to {mapped_id}"
                )
            destinations.add(mapped_id)
            remapped_targets.append({**target, "entity_id": mapped_id})
        candidate = validate_scene({**candidate, "targets": remapped_targets})
        fingerprint = _fingerprint(candidate)
        previous_fingerprint = source_id_fingerprints.setdefault(candidate["id"], fingerprint)
        if previous_fingerprint != fingerprint:
            raise ValueError(
                f"Conflicting scene definitions share source UUID {candidate['id']}"
            )
        normalized.append((candidate, provenance, unmapped_for_scene))

    unused_mappings = mappings.keys() - referenced_targets
    if unused_mappings:
        raise ValueError(
            f"Target mappings do not match bundled lights: {', '.join(sorted(unused_mappings))}"
        )

    used_ids = {scene["id"] for scene in builtins}
    existing_fingerprints: dict[str, str] = {}
    for scene in existing_scenes:
        normalized_scene = validate_scene(scene)
        scene_id = normalized_scene["id"]
        used_ids.add(scene_id)
        existing_fingerprints.setdefault(_fingerprint(normalized_scene), scene_id)

    planned_fingerprints: dict[str, str] = {}
    planned_scenes: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    unmapped_targets: set[str] = set()

    for candidate, provenance, original_target_ids in normalized:
        source_id = candidate["id"]
        unmapped_targets.update(original_target_ids)
        fingerprint = _fingerprint(candidate)
        duplicate_id = existing_fingerprints.get(fingerprint) or planned_fingerprints.get(
            fingerprint
        )
        if duplicate_id is not None:
            items.append(
                {
                    "source_id": source_id,
                    "scene_id": duplicate_id,
                    "name": candidate["name"],
                    "action": "skip_duplicate",
                    "identity": "existing",
                    "target_count": len(candidate["targets"]),
                    "unmapped_targets": sorted(original_target_ids),
                    "source_provenance": provenance,
                }
            )
            continue

        scene_id = source_id
        identity = "preserved"
        if scene_id in used_ids:
            identity = "derived"
            salt = 0
            while True:
                identity_seed = f"{source_id}:{fingerprint}:{salt}"
                scene_id = str(uuid5(NAMESPACE_URL, f"{DOMAIN}:import:v1:{identity_seed}"))
                if scene_id not in used_ids:
                    break
                salt += 1

        imported = validate_scene(
            {
                **candidate,
                "id": scene_id,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        )
        used_ids.add(scene_id)
        planned_fingerprints[fingerprint] = scene_id
        planned_scenes.append(imported)
        items.append(
            {
                "source_id": source_id,
                "scene_id": scene_id,
                "name": imported["name"],
                "action": "import",
                "identity": identity,
                "target_count": len(imported["targets"]),
                "unmapped_targets": sorted(original_target_ids),
                "source_provenance": provenance,
            }
        )

    return {
        "scenes": planned_scenes,
        "items": items,
        "unmapped_targets": sorted(unmapped_targets),
        "imported_count": len(planned_scenes),
        "skipped_count": len(items) - len(planned_scenes),
    }


def import_report(
    plan: dict[str, Any], *, dry_run: bool, capacity: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Return an API-safe report without exposing internal mutable scene objects."""
    report = {
        "dry_run": dry_run,
        "scenes": deepcopy(plan["items"]),
        "imported_count": plan["imported_count"],
        "skipped_count": plan["skipped_count"],
        "unmapped_targets": list(plan["unmapped_targets"]),
    }
    if capacity is not None:
        report["capacity"] = deepcopy(capacity)
    return report


def _export_scene(scene: dict[str, Any]) -> dict[str, Any]:
    """Keep exports restricted to validated scene model fields."""
    allowlisted = {key: value for key, value in scene.items() if key in _SCENE_FIELDS}
    validated = validate_scene(allowlisted)
    exported = {key: deepcopy(validated[key]) for key in _SCENE_FIELD_ORDER}
    for timestamp_key in ("created_at", "updated_at"):
        if not isinstance(exported[timestamp_key], str):
            exported[timestamp_key] = None
    return exported


def _validate_target_mappings(value: Any) -> dict[str, str]:
    """Validate explicit source-to-destination light mappings."""
    if not isinstance(value, dict):
        raise ValueError("target_mappings must be an object")
    mappings: dict[str, str] = {}
    for source_id, destination_id in value.items():
        if not _valid_light_entity_id(source_id) or not _valid_light_entity_id(destination_id):
            raise ValueError("Target mappings must contain valid light entity IDs")
        mappings[source_id] = destination_id
    return mappings


def _valid_light_entity_id(value: Any) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) <= 255
        and _LIGHT_ENTITY_ID.fullmatch(value)
    )


def _fingerprint(scene: dict[str, Any]) -> str:
    content = {key: scene[key] for key in _CONTENT_FIELDS}
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_bundle_size(value: Any) -> None:
    try:
        serialized = json.dumps(value, separators=(",", ":"), ensure_ascii=True)
    except (TypeError, ValueError) as err:
        raise ValueError("Scene bundle must contain JSON-compatible values") from err
    if len(serialized.encode("utf-8")) > MAX_BUNDLE_BYTES:
        raise ValueError("Scene bundle exceeds the 1 MiB limit")
