"""Read-only conversion and import planning for cached Hue V2 resources."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from homeassistant.components.light import ColorMode
from homeassistant.util.color import color_xy_to_RGB

from .const import DOMAIN
from .models import validate_scene
from .scene_bundle import plan_scene_import

MAX_HUE_SCENES = 500
MAX_HUE_RESOURCE_BYTES = 4 * 1024 * 1024
MAX_HUE_ACTIONS = 64
_NEUTRAL_PALETTE = ["#FFFFFF", "#808080"]


def convert_hue_v2_resources(
    scenes: Any,
    lights: Any,
    groups: Any,
    bridge_id: str,
    target_mappings: Any,
    *,
    available_targets: Mapping[str, Mapping[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Convert simulated or cached Hue resource payloads to portable static scenes.

    Hue IDs are never treated as Home Assistant entity IDs. Every destination is
    supplied explicitly by the caller; unmapped source actions stay in source
    metadata so a later mapping can be applied without losing the imported data.
    """
    scene_resources = _resources(scenes, {"scene"})
    light_resources = _resources(lights, {"light"})
    group_resources = _resources(groups, {"room", "zone"})
    _check_snapshot_size((scenes, lights, groups))
    if len(scene_resources) > MAX_HUE_SCENES:
        raise ValueError(f"Hue returned more than {MAX_HUE_SCENES} scenes")
    if not isinstance(bridge_id, str) or not 1 <= len(bridge_id) <= 128:
        raise ValueError("Invalid Hue bridge identity")
    if not isinstance(target_mappings, Mapping):
        raise ValueError("target_mappings must be an object")
    mappings = _validate_mappings(target_mappings)
    available_targets = available_targets or {}
    lights_by_id = {item["id"]: item for item in light_resources}
    groups_by_id = {item["id"]: item for item in group_resources}
    converted: list[dict[str, Any]] = []
    report: dict[str, set[str]] = {
        "unmapped_light_ids": set(),
        "missing_light_ids": set(),
        "unsupported_features": set(),
    }
    seen_ids: set[str] = set()
    referenced_ids = {
        _object(_object(action).get("target")).get("rid")
        for scene in scene_resources
        for action in _object(scene).get("actions", [])
    }
    if unknown := mappings.keys() - referenced_ids:
        raise ValueError(f"Hue light mappings reference unknown IDs: {', '.join(sorted(unknown))}")

    for resource in scene_resources:
        scene_id = _uuid(resource.get("id"), "Hue scene id")
        if scene_id in seen_ids:
            raise ValueError(f"Duplicate Hue scene ID: {scene_id}")
        seen_ids.add(scene_id)
        metadata = _object(resource.get("metadata"))
        name = metadata.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Hue scene {scene_id} has no valid metadata.name")
        name = name.strip()[:80]
        group_link = _object(resource.get("group"))
        group_id = _uuid(group_link.get("rid"), "Hue scene group id", optional=True)
        group = groups_by_id.get(group_id) if group_id else None
        group_metadata = _object(_object(group).get("metadata")) if group else {}
        group_name = group_metadata.get("name")

        raw_actions = resource.get("actions", [])
        if not isinstance(raw_actions, list) or len(raw_actions) > MAX_HUE_ACTIONS:
            raise ValueError(f"Hue scene {scene_id} exceeds the action limit")
        palette: list[str] = []
        source_actions: list[dict[str, Any]] = []
        targets: list[dict[str, Any]] = []
        unmapped: set[str] = set()
        missing: set[str] = set()
        unsupported: set[str] = set()
        used_destinations: set[str] = set()
        for raw_action in raw_actions:
            action = _object(raw_action)
            target_link = _object(action.get("target"))
            source_light_id = _uuid(target_link.get("rid"), "Hue action target id")
            if target_link.get("rtype") not in (None, "light"):
                unsupported.add("non_light_scene_target")
                continue
            if source_light_id not in lights_by_id:
                missing.add(source_light_id)
            action_data = _action_data(source_light_id, action.get("action"))
            source_actions.append(action_data)
            mapped_entity = mappings.get(source_light_id)
            if mapped_entity is None:
                unmapped.add(source_light_id)
                continue
            if mapped_entity in used_destinations:
                raise ValueError(f"Multiple Hue lights in scene {scene_id} map to {mapped_entity}")
            used_destinations.add(mapped_entity)
            if mapped_entity not in available_targets:
                missing.add(source_light_id)
            target, target_unsupported = _target_from_action(
                action_data,
                mapped_entity,
                available_targets.get(mapped_entity),
                len(targets),
            )
            targets.append(target)
            unsupported.update(target_unsupported)
            if "xy" in action_data and _state_for_xy_available(
                available_targets.get(mapped_entity)
            ):
                unsupported.add("target_color_gamut_not_verified")
            if target.get("color"):
                palette.append(target["color"])

        auto_dynamic = bool(resource.get("auto_dynamic", False))
        hue_palette = _plain(resource.get("palette"))
        if auto_dynamic:
            unsupported.add("auto_dynamic")
        if _has_gradient(resource):
            unsupported.add("gradient")
        if _has_effect(resource):
            unsupported.add("dynamic_effect")
        if _palette_is_dynamic(hue_palette):
            unsupported.add("dynamic_palette")
        if any(key in resource for key in ("image", "images")):
            unsupported.add("scene_images_not_transferred")
        speed = resource.get("speed")
        if speed is not None and not _is_number_between(speed, 0, 1):
            speed = None
            unsupported.add("invalid_speed")
        if isinstance(hue_palette, (dict, list)):
            try:
                if len(json.dumps(hue_palette, separators=(",", ":")).encode()) > 32_768:
                    hue_palette = None
                    unsupported.add("oversized_palette_metadata")
            except (TypeError, ValueError):
                hue_palette = None
                unsupported.add("invalid_palette_metadata")

        if not palette:
            palette = list(_NEUTRAL_PALETTE)
        if len(palette) == 1:
            palette.append("#000000" if palette[0] != "#000000" else "#FFFFFF")
        unique_palette = list(dict.fromkeys(color.upper() for color in palette))[:8]
        if len(unique_palette) == 1:
            unique_palette.append("#000000" if unique_palette[0] != "#000000" else "#FFFFFF")

        source: dict[str, Any] = {
            "provider": "hue_v2",
            "id": scene_id,
            "bridge_id": bridge_id,
            "name": name,
            "unmapped_light_ids": sorted(unmapped),
            "missing_light_ids": sorted(missing),
            "unsupported_features": sorted(unsupported),
            "auto_dynamic": auto_dynamic,
            "source_actions": source_actions,
        }
        if group_id is not None:
            source["group_id"] = group_id
        if isinstance(group_name, str):
            source["group_name"] = group_name[:255]
        if speed is not None:
            source["speed"] = speed
        if isinstance(hue_palette, dict):
            source["hue_palette"] = hue_palette
        local_id = str(uuid5(NAMESPACE_URL, f"{DOMAIN}:hue-v2:{bridge_id}:{scene_id}"))
        converted_scene = validate_scene(
            {
                "id": local_id,
                "name": name,
                "kind": "static",
                "category": "hue_import",
                "palette": unique_palette,
                "targets": targets,
                "brightness_pct": 80,
                "transition": 0,
                "source": source,
            }
        )
        converted.append(converted_scene)
        report["unmapped_light_ids"].update(unmapped)
        report["missing_light_ids"].update(missing)
        report["unsupported_features"].update(unsupported)

    return converted, {key: sorted(values) for key, values in report.items()}


def plan_hue_scene_import(
    converted_scenes: list[dict[str, Any]],
    existing_scenes: tuple[dict[str, Any], ...],
    builtins: list[dict[str, Any]],
    *,
    now: str | None = None,
) -> dict[str, Any]:
    """Plan idempotent imports keyed by bridge and original Hue scene ID."""
    existing_sources = {
        (
            (scene.get("source") or {}).get("bridge_id", ""),
            (scene.get("source") or {}).get("id", ""),
        )
        for scene in existing_scenes
        if isinstance(scene.get("source"), dict) and scene["source"].get("provider") == "hue_v2"
    }
    to_import = [
        scene
        for scene in converted_scenes
        if ((scene["source"]["bridge_id"], scene["source"]["id"]) not in existing_sources)
    ]
    already_imported = [scene for scene in converted_scenes if scene not in to_import]
    if to_import:
        plan = plan_scene_import(
            {
                "format": "smart_scene_studio.scene_bundle",
                "version": 1,
                "scenes": [{**scene, "provenance": "hue_import"} for scene in to_import],
            },
            {},
            existing_scenes,
            builtins,
            now=now,
            deduplicate_content=False,
            remap_targets=False,
        )
    else:
        plan = {
            "scenes": [],
            "items": [],
            "unmapped_targets": [],
            "imported_count": 0,
            "skipped_count": 0,
        }
    plan["items"] = [
        {
            **item,
            "source_id": scene["source"]["id"],
            "bridge_id": scene["source"]["bridge_id"],
            "source_provenance": "hue_import",
        }
        for item, scene in zip(plan["items"], to_import, strict=True)
    ]
    plan["items"].extend(
        {
            "source_id": scene["source"]["id"],
            "bridge_id": scene["source"]["bridge_id"],
            "scene_id": scene["id"],
            "name": scene["name"],
            "action": "skip_imported",
            "identity": "source",
            "target_count": len(scene["targets"]),
            "unmapped_targets": scene["source"]["unmapped_light_ids"],
            "source_provenance": "hue_import",
        }
        for scene in already_imported
    )
    plan["skipped_count"] += len(already_imported)
    return plan


def hue_resource_to_dict(value: Any) -> Any:
    """Convert aiohue resource models to a detached JSON-like structure."""
    return _plain(value)


def remap_hue_scene_targets(
    scene: dict[str, Any],
    target_mappings: Any,
    *,
    available_targets: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Apply explicit or deferred Hue light mappings while preserving the palette."""
    source = scene.get("source")
    if not isinstance(source, dict) or source.get("provider") != "hue_v2":
        raise ValueError("Scene is not a Hue V2 import")
    actions = source.get("source_actions", [])
    if not actions:
        raise ValueError("Hue scene has no preserved source actions to map")
    mappings = _validate_mappings(target_mappings)
    source_ids = {action["light_id"] for action in actions}
    if unknown := mappings.keys() - source_ids:
        raise ValueError(
            f"Mappings reference lights outside this Hue scene: {', '.join(sorted(unknown))}"
        )
    available_targets = available_targets or {}
    existing_targets = {target.get("source_id"): target for target in scene.get("targets", [])}
    targets: list[dict[str, Any]] = []
    missing = set(source.get("missing_light_ids", []))
    unsupported = set(source.get("unsupported_features", [])) - {
        "mapped_target_unavailable",
        "mapped_target_does_not_support_xy",
        "mapped_target_does_not_support_color_temperature",
        "target_color_gamut_not_verified",
        "color_temperature_clamped_to_target_range",
    }
    used_destinations: set[str] = set()
    for action in actions:
        destination = mappings.get(action["light_id"])
        if destination is None:
            continue
        if destination in used_destinations:
            raise ValueError(f"Multiple Hue lights map to {destination}")
        used_destinations.add(destination)
        state = available_targets.get(destination)
        old = existing_targets.get(action["light_id"], {})
        target, target_unsupported = _target_from_action(
            action,
            destination,
            state,
            old.get("color_index", len(targets) % len(scene["palette"])),
        )
        targets.append(target)
        unsupported.update(target_unsupported)
        if "xy" in action and _state_for_xy_available(state):
            unsupported.add("target_color_gamut_not_verified")
        if state is None:
            missing.add(action["light_id"])
        else:
            missing.discard(action["light_id"])
    source_updated = {
        **source,
        "unmapped_light_ids": sorted(source_ids - mappings.keys()),
        "missing_light_ids": sorted(missing),
        "unsupported_features": sorted(unsupported),
    }
    return validate_scene({**scene, "targets": targets, "source": source_updated})


def _resources(value: Any, types: set[str]) -> list[dict[str, Any]]:
    if isinstance(value, Mapping):
        raw = value.get("data", [value])
    else:
        raw = value
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
        raise ValueError("Hue resource collection must be a JSON list")
    result = []
    for entry in raw:
        resource = _plain(entry)
        if not isinstance(resource, dict) or resource.get("type") not in types:
            continue
        result.append(resource)
    return result


def _action_data(source_id: str, value: Any) -> dict[str, Any]:
    action = _object(value)
    on = _object(action.get("on"))
    dimming = _object(action.get("dimming"))
    color = _object(action.get("color"))
    xy = _object(color.get("xy"))
    temp = _object(action.get("color_temperature"))
    if not temp:
        temp = _object(action.get("color_temperature_mirek"))
    result: dict[str, Any] = {"light_id": source_id}
    if isinstance(on.get("on"), bool):
        result["on"] = on["on"]
    brightness = dimming.get("brightness")
    if _is_number_between(brightness, 0, 100):
        result["brightness"] = float(brightness)
    if _is_number_between(xy.get("x"), 0, 1) and _is_number_between(xy.get("y"), 0, 1):
        if 0 < xy["x"] + xy["y"] <= 1:
            result["xy"] = [float(xy["x"]), float(xy["y"])]
    mirek = temp.get("mirek")
    if isinstance(mirek, int) and not isinstance(mirek, bool) and mirek > 0:
        result["mirek"] = mirek
    return result


def _target_from_action(
    action: dict[str, Any],
    entity_id: str,
    state: Mapping[str, Any] | None,
    color_index: int,
) -> tuple[dict[str, Any], set[str]]:
    unsupported: set[str] = set()
    target: dict[str, Any] = {
        "entity_id": entity_id,
        "enabled": state is not None,
        "color_index": color_index,
        "source_id": action["light_id"],
        "state": "on" if action.get("on", True) else "off",
    }
    if state is None:
        unsupported.add("mapped_target_unavailable")
    if "brightness" in action:
        target["brightness_pct"] = max(1, round(action["brightness"]))
    if "xy" in action:
        xy = action["xy"]
        target["color_xy"] = xy
        target["color"] = _xy_to_hex(xy)
        target["color_mode"] = "xy"
        if state is not None and ColorMode.XY not in set(state.get("supported_color_modes", ())):
            target["enabled"] = False
            unsupported.add("mapped_target_does_not_support_xy")
    elif "mirek" in action:
        target["color_temp_kelvin"] = max(1000, min(10000, round(1_000_000 / action["mirek"])))
        target["color"] = "#FFFFFF"
        target["color_mode"] = "color_temp_kelvin"
        if state is not None:
            attrs = state
            modes = set(attrs.get("supported_color_modes", ()))
            minimum = attrs.get("min_color_temp_kelvin")
            maximum = attrs.get("max_color_temp_kelvin")
            if (
                ColorMode.COLOR_TEMP not in modes
                or not isinstance(minimum, int)
                or not isinstance(maximum, int)
            ):
                target["enabled"] = False
                unsupported.add("mapped_target_does_not_support_color_temperature")
            elif not minimum <= target["color_temp_kelvin"] <= maximum:
                target["color_temp_kelvin"] = min(
                    maximum, max(minimum, target["color_temp_kelvin"])
                )
                unsupported.add("color_temperature_clamped_to_target_range")
    elif action.get("on", True):
        target["color_mode"] = "none"
    return target, unsupported


def _xy_to_hex(xy: list[float]) -> str:
    rgb = color_xy_to_RGB(xy[0], xy[1])
    return "#" + "".join(f"{component:02X}" for component in rgb)


def _validate_mappings(value: Mapping[str, Any]) -> dict[str, str]:
    if len(value) > MAX_HUE_ACTIONS * MAX_HUE_SCENES:
        raise ValueError("Too many Hue light mappings")
    result: dict[str, str] = {}
    for source, destination in value.items():
        source_id = _uuid(source, "Hue light mapping ID")
        if (
            not isinstance(destination, str)
            or len(destination) > 255
            or not destination.startswith("light.")
            or not all(
                part and part.replace("_", "").isalnum() for part in destination[6:].split(".")
            )
        ):
            raise ValueError("Hue light mappings must target valid light.* entity IDs")
        result[source_id] = destination
    return result


def _uuid(value: Any, label: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    try:
        return str(UUID(value))
    except (TypeError, ValueError) as err:
        raise ValueError(f"{label} must be a UUID") from err


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return _plain(value.value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_plain(item) for item in value]
    if hasattr(value, "model_dump"):
        return _plain(value.model_dump(mode="json", exclude_none=True))
    if hasattr(value, "to_dict"):
        return _plain(value.to_dict())
    if hasattr(value, "__attrs_attrs__"):
        return {
            attribute.name: _plain(getattr(value, attribute.name))
            for attribute in value.__attrs_attrs__
            if getattr(value, attribute.name) is not None
        }
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _plain(getattr(value, item.name))
            for item in fields(value)
            if getattr(value, item.name) is not None
        }
    if hasattr(value, "__dict__"):
        return {
            key: _plain(item)
            for key, item in vars(value).items()
            if not key.startswith("_") and item is not None
        }
    slots = getattr(type(value), "__slots__", ())
    if isinstance(slots, str):
        slots = (slots,)
    return {
        key: _plain(getattr(value, key))
        for key in slots
        if not key.startswith("_") and hasattr(value, key) and getattr(value, key) is not None
    }


def _palette_is_dynamic(palette: Any) -> bool:
    if not isinstance(palette, dict):
        return False
    return any(
        isinstance(palette.get(key), list) and len(palette[key]) > 1
        for key in ("color", "color_temperature", "dimming")
    )


def _has_gradient(resource: dict[str, Any]) -> bool:
    serialized = json.dumps(resource, default=str).casefold()
    return "gradient" in serialized


def _has_effect(resource: dict[str, Any]) -> bool:
    palette = resource.get("palette")
    if isinstance(palette, dict) and palette.get("effects"):
        return True
    return bool(resource.get("effects"))


def _is_number_between(value: Any, minimum: int | float, maximum: int | float) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and minimum <= value <= maximum
    )


def _state_for_xy_available(state: Mapping[str, Any] | None) -> bool:
    """Whether a mapped target advertises XY; its actual gamut is still device-specific."""
    return state is not None and ColorMode.XY in set(state.get("supported_color_modes", ()))


def _check_snapshot_size(value: Any) -> None:
    try:
        size = len(json.dumps(value, separators=(",", ":"), default=str).encode())
    except (TypeError, ValueError) as err:
        raise ValueError("Hue resources are not serializable") from err
    if size > MAX_HUE_RESOURCE_BYTES:
        raise ValueError("Hue resource snapshot exceeds the 4 MiB limit")
