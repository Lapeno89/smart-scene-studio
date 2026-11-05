"""Validated scene definition helpers."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_COLOR_MODES = {"xy", "rgb", "hs", "rgbw", "rgbww", "color_temp_kelvin", "brightness", "none"}


def validate_scene(value: Any) -> dict[str, Any]:
    """Validate and normalize a v1 static scene without dropping unknown data."""
    if not isinstance(value, dict):
        raise ValueError("Scene must be an object")
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
            or not entity_id.startswith("light.")
            or len(entity_id) > 255
        ):
            raise ValueError("Target entity_id must be a light entity")
        if entity_id in seen:
            continue
        seen.add(entity_id)
        mode = target.get("color_mode")
        if mode is not None and mode not in _COLOR_MODES:
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
        checked_targets.append(item)
    favorite = value.get("favorite", False)
    if not isinstance(favorite, bool):
        raise ValueError("favorite must be boolean")
    brightness_pct = value.get("brightness_pct", 80)
    transition = value.get("transition", 0)
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
        "created_at": value.get("created_at"),
        "updated_at": value.get("updated_at"),
    }


def scene_object_id(scene: dict[str, Any]) -> str:
    """Create a readable entity object id; identity is the immutable UUID."""
    value = re.sub(r"[^a-z0-9]+", "_", scene["name"].casefold()).strip("_")
    return value or scene["id"].replace("-", "")
