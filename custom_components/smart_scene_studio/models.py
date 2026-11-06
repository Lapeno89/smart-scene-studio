"""Validated scene definition helpers."""

from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_COLOR_MODES = {"xy", "rgb", "hs", "rgbw", "rgbww", "color_temp_kelvin", "brightness", "none"}
_TARGET_FIELDS = {
    "entity_id",
    "enabled",
    "color_index",
    "state",
    "color_mode",
    "color",
    "brightness_pct",
    "transition",
    "color_temp_kelvin",
    "color_xy",
    "source_id",
}
_SCENE_FIELDS = {
    "id",
    "name",
    "kind",
    "category",
    "favorite",
    "palette",
    "targets",
    "brightness_pct",
    "transition",
    "white_temperature_kelvin",
    "created_at",
    "updated_at",
    "source",
}


def validate_scene(value: Any) -> dict[str, Any]:
    """Validate and normalize a v1 static scene, rejecting unknown fields."""
    if not isinstance(value, dict):
        raise ValueError("Scene must be an object")
    unknown_fields = value.keys() - _SCENE_FIELDS
    if unknown_fields:
        raise ValueError(f"Unsupported scene fields: {', '.join(sorted(unknown_fields))}")
    try:
        scene_id = str(UUID(value["id"]))
    except (KeyError, TypeError, ValueError) as err:
        raise ValueError("Scene id must be a UUID") from err
    name = value.get("name")
    if not isinstance(name, str) or not name.strip() or len(name) > 80:
        raise ValueError("Scene name must contain 1 to 80 characters")
    if value.get("kind") != "static":
        raise ValueError("Only static scenes are supported")
    category = value.get("category", "custom")
    if not isinstance(category, str) or not category.strip() or len(category) > 40:
        raise ValueError("Invalid category")
    palette = value.get("palette")
    if not isinstance(palette, list) or not 2 <= len(palette) <= 8:
        raise ValueError("Palette must contain 2 to 8 colors")
    if any(not isinstance(color, str) or not _HEX_COLOR.fullmatch(color) for color in palette):
        raise ValueError("Palette colors must be RGB hex values")
    targets = value.get("targets", [])
    if not isinstance(targets, list) or len(targets) > 64:
        raise ValueError("Targets must be a list with at most 64 entries")
    checked_targets = []
    seen: set[str] = set()
    for target in targets:
        if not isinstance(target, dict):
            raise ValueError("Each target must be an object")
        entity_id = target.get("entity_id")
        if (
            not isinstance(entity_id, str)
            or not re.fullmatch(r"light\.[a-z0-9_]+", entity_id)
            or len(entity_id) > 255
        ):
            raise ValueError("Target entity_id must be a light entity")
        if extra_fields := target.keys() - _TARGET_FIELDS:
            raise ValueError(f"Unsupported target fields: {', '.join(sorted(extra_fields))}")
        if entity_id in seen:
            continue
        seen.add(entity_id)
        mode = target.get("color_mode")
        if mode is not None and (not isinstance(mode, str) or mode not in _COLOR_MODES):
            raise ValueError("Unsupported color mode")
        color_index = target.get("color_index", len(checked_targets) % len(palette))
        if (
            not isinstance(color_index, int)
            or isinstance(color_index, bool)
            or not 0 <= color_index < len(palette)
        ):
            raise ValueError("Target color_index is outside the palette")
        item: dict[str, Any] = {
            "entity_id": entity_id,
            "enabled": target.get("enabled", True),
            "color_index": color_index,
            "state": target.get("state", "on"),
        }
        if not isinstance(item["enabled"], bool):
            raise ValueError("Target enabled must be boolean")
        if item["state"] not in ("on", "off"):
            raise ValueError("Target state must be 'on' or 'off'")
        if mode is not None:
            item["color_mode"] = mode
        source_id = target.get("source_id")
        if source_id is not None:
            try:
                item["source_id"] = str(UUID(source_id))
            except (TypeError, ValueError) as err:
                raise ValueError("Target source_id must be a UUID") from err
        color = target.get("color")
        if color is not None:
            if not isinstance(color, str) or not _HEX_COLOR.fullmatch(color):
                raise ValueError("Target color must be an RGB hex value")
            item["color"] = color.upper()
        for numeric_key, low, high in (("brightness_pct", 1, 100), ("transition", 0, 300)):
            numeric = target.get(numeric_key)
            if numeric is not None:
                if (
                    not isinstance(numeric, (int, float))
                    or isinstance(numeric, bool)
                    or not low <= numeric <= high
                ):
                    raise ValueError(f"Invalid {numeric_key}")
                item[numeric_key] = numeric
        kelvin = target.get("color_temp_kelvin")
        if kelvin is not None:
            if (
                not isinstance(kelvin, int)
                or isinstance(kelvin, bool)
                or not 1000 <= kelvin <= 10000
            ):
                raise ValueError("Invalid color_temp_kelvin")
            item["color_temp_kelvin"] = kelvin
        xy = target.get("color_xy")
        if xy is not None:
            if (
                not isinstance(xy, (list, tuple))
                or len(xy) != 2
                or any(
                    not isinstance(value, (int, float))
                    or isinstance(value, bool)
                    or not 0 <= value <= 1
                    for value in xy
                )
                or sum(xy) <= 0
                or sum(xy) > 1
            ):
                raise ValueError("Target color_xy must be a valid CIE xy pair")
            item["color_xy"] = [float(value) for value in xy]
        checked_targets.append(item)
    favorite = value.get("favorite", False)
    if not isinstance(favorite, bool):
        raise ValueError("favorite must be boolean")
    brightness_pct = value.get("brightness_pct", 80)
    transition = value.get("transition", 0)
    white_temperature_kelvin = value.get("white_temperature_kelvin")
    if (
        not isinstance(brightness_pct, (int, float))
        or isinstance(brightness_pct, bool)
        or not 1 <= brightness_pct <= 100
    ):
        raise ValueError("Invalid scene brightness_pct")
    if (
        not isinstance(transition, (int, float))
        or isinstance(transition, bool)
        or not 0 <= transition <= 300
    ):
        raise ValueError("Invalid scene transition")
    if white_temperature_kelvin is not None and (
        not isinstance(white_temperature_kelvin, int)
        or isinstance(white_temperature_kelvin, bool)
        or not 1000 <= white_temperature_kelvin <= 10000
    ):
        raise ValueError("Invalid scene white_temperature_kelvin")
    source = value.get("source")
    if source is not None:
        source = _validate_scene_source(source)
    return {
        "id": scene_id,
        "name": name.strip(),
        "kind": "static",
        "category": category.strip(),
        "favorite": favorite,
        "palette": [color.upper() for color in palette],
        "targets": checked_targets,
        "brightness_pct": brightness_pct,
        "transition": transition,
        "white_temperature_kelvin": white_temperature_kelvin,
        "created_at": value.get("created_at"),
        "updated_at": value.get("updated_at"),
        "source": source,
    }


def _validate_scene_source(value: Any) -> dict[str, Any]:
    """Validate portable, non-secret Hue import provenance."""
    fields = {
        "provider",
        "id",
        "bridge_id",
        "name",
        "group_id",
        "group_name",
        "unmapped_light_ids",
        "missing_light_ids",
        "unsupported_features",
        "auto_dynamic",
        "speed",
        "hue_palette",
        "source_actions",
    }
    if not isinstance(value, dict) or value.keys() - fields:
        raise ValueError("Invalid scene source metadata")
    if value.get("provider") != "hue_v2":
        raise ValueError("Unsupported scene source provider")
    try:
        source_id = str(UUID(value["id"]))
        if value.get("group_id") is not None:
            group_id = str(UUID(value["group_id"]))
        else:
            group_id = None
    except (KeyError, TypeError, ValueError) as err:
        raise ValueError("Hue source and group IDs must be UUIDs") from err
    bridge_id = value.get("bridge_id")
    name = value.get("name")
    if not isinstance(bridge_id, str) or not 1 <= len(bridge_id) <= 128:
        raise ValueError("Invalid Hue bridge source ID")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 255:
        raise ValueError("Invalid Hue source scene name")
    result: dict[str, Any] = {
        "provider": "hue_v2",
        "id": source_id,
        "bridge_id": bridge_id,
        "name": name.strip(),
    }
    if group_id is not None:
        result["group_id"] = group_id
    group_name = value.get("group_name")
    if group_name is not None:
        if not isinstance(group_name, str) or len(group_name) > 255:
            raise ValueError("Invalid Hue source group name")
        result["group_name"] = group_name
    for field in ("unmapped_light_ids", "missing_light_ids", "unsupported_features"):
        items = value.get(field, [])
        if (
            not isinstance(items, list)
            or len(items) > 64
            or any(not isinstance(item, str) or len(item) > 128 for item in items)
        ):
            raise ValueError(f"Invalid Hue source {field}")
        result[field] = list(dict.fromkeys(items))
    auto_dynamic = value.get("auto_dynamic", False)
    if not isinstance(auto_dynamic, bool):
        raise ValueError("Hue auto_dynamic must be boolean")
    result["auto_dynamic"] = auto_dynamic
    speed = value.get("speed")
    if speed is not None:
        if not isinstance(speed, (int, float)) or isinstance(speed, bool) or not 0 <= speed <= 1:
            raise ValueError("Invalid Hue scene speed")
        result["speed"] = speed
    palette = value.get("hue_palette")
    if palette is not None:
        if (
            not isinstance(palette, dict)
            or len(json.dumps(palette, separators=(",", ":"), ensure_ascii=True).encode()) > 32_768
        ):
            raise ValueError("Invalid or oversized Hue palette metadata")
        result["hue_palette"] = palette
    actions = value.get("source_actions", [])
    if not isinstance(actions, list) or len(actions) > 64:
        raise ValueError("Invalid Hue source actions")
    checked_actions = []
    for action in actions:
        if not isinstance(action, dict) or action.keys() - {
            "light_id",
            "on",
            "brightness",
            "xy",
            "mirek",
        }:
            raise ValueError("Invalid Hue source action")
        try:
            light_id = str(UUID(action["light_id"]))
        except (KeyError, TypeError, ValueError) as err:
            raise ValueError("Hue source action light_id must be a UUID") from err
        checked = {"light_id": light_id}
        on = action.get("on")
        if on is not None:
            if not isinstance(on, bool):
                raise ValueError("Hue source action on must be boolean")
            checked["on"] = on
        brightness = action.get("brightness")
        if brightness is not None:
            if (
                not isinstance(brightness, (int, float))
                or isinstance(brightness, bool)
                or not 0 <= brightness <= 100
            ):
                raise ValueError("Invalid Hue source action brightness")
            checked["brightness"] = brightness
        xy = action.get("xy")
        if xy is not None:
            if (
                not isinstance(xy, list)
                or len(xy) != 2
                or any(
                    not isinstance(component, (int, float))
                    or isinstance(component, bool)
                    or not 0 <= component <= 1
                    for component in xy
                )
                or sum(xy) <= 0
                or sum(xy) > 1
            ):
                raise ValueError("Invalid Hue source action xy")
            checked["xy"] = [float(component) for component in xy]
        mirek = action.get("mirek")
        if mirek is not None:
            if not isinstance(mirek, int) or isinstance(mirek, bool) or mirek <= 0:
                raise ValueError("Invalid Hue source action mirek")
            checked["mirek"] = mirek
        checked_actions.append(checked)
    if len(json.dumps(checked_actions, separators=(",", ":")).encode()) > 65_536:
        raise ValueError("Hue source actions exceed the 64 KiB limit")
    result["source_actions"] = checked_actions
    return result


def scene_object_id(scene: dict[str, Any]) -> str:
    """Create a readable entity object id; identity is the immutable UUID."""
    value = re.sub(r"[^a-z0-9]+", "_", scene["name"].casefold()).strip("_")
    return value or scene["id"].replace("-", "")
