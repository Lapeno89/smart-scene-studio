"""Capability-aware Home Assistant light service adapter."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS_PCT,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_TRANSITION,
    ATTR_XY_COLOR,
    SERVICE_TURN_ON,
    ColorMode,
    LightEntityFeature,
)
from homeassistant.components.light import (
    DOMAIN as LIGHT_DOMAIN,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.color import color_RGB_to_xy


async def async_apply_scene(
    hass: HomeAssistant,
    scene: dict[str, Any],
    targets: list[str] | None = None,
) -> dict[str, Any]:
    """Apply colors sequentially, skipping absent, unavailable or incompatible lights."""
    assignments = scene.get("targets", [])
    selected = list(dict.fromkeys(targets or [item["entity_id"] for item in assignments]))
    by_id = {item["entity_id"]: item for item in assignments}
    results = {"applied": [], "skipped": [], "failed": []}
    for index, entity_id in enumerate(selected):
        state = hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            results["skipped"].append(entity_id)
            continue
        attrs = state.attributes
        modes = attrs.get("supported_color_modes", ())
        assignment = by_id.get(entity_id, {})
        mode = assignment.get("color_mode")
        payload: dict[str, Any] = {}
        palette = scene["palette"]
        color_index = assignment.get("color_index", index)
        rgb = tuple(
            int(palette[color_index % len(palette)][offset : offset + 2], 16)
            for offset in (1, 3, 5)
        )
        if mode is None and ColorMode.XY in modes:
            mode = "xy"
        elif mode is None and ColorMode.RGB in modes:
            mode = "rgb"
        if mode == "xy" and ColorMode.XY in modes:
            payload[ATTR_XY_COLOR] = color_RGB_to_xy(*rgb)
        elif mode == "rgb" and ColorMode.RGB in modes:
            payload[ATTR_RGB_COLOR] = rgb
        elif mode == "color_temp_kelvin" and ColorMode.COLOR_TEMP in modes:
            # This first slice does not guess a white point from a colorful palette.
            kelvin = assignment.get("color_temp_kelvin")
            kelvin_range = attrs.get("min_color_temp_kelvin"), attrs.get("max_color_temp_kelvin")
            if not isinstance(kelvin, int) or not all(isinstance(v, int) for v in kelvin_range):
                results["skipped"].append(entity_id)
                continue
            payload[ATTR_COLOR_TEMP_KELVIN] = min(kelvin_range[1], max(kelvin_range[0], kelvin))
        elif mode == "brightness" and modes:
            pass
        else:
            results["skipped"].append(entity_id)
            continue
        brightness = assignment.get("brightness_pct", scene.get("brightness_pct"))
        if brightness is not None and any(m != ColorMode.ONOFF for m in modes):
            payload[ATTR_BRIGHTNESS_PCT] = brightness
        transition = assignment.get("transition", scene.get("transition"))
        features = attrs.get("supported_features", 0)
        if transition and features & LightEntityFeature.TRANSITION:
            payload[ATTR_TRANSITION] = transition
        try:
            await hass.services.async_call(
                LIGHT_DOMAIN,
                SERVICE_TURN_ON,
                {"entity_id": entity_id, **payload},
                blocking=True,
            )
        except HomeAssistantError:
            results["failed"].append(entity_id)
        else:
            results["applied"].append(entity_id)
    return results
