"""Capability-aware Home Assistant light service adapter."""

from __future__ import annotations

from typing import Any

from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.components.light import (
    ATTR_BRIGHTNESS_PCT,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ATTR_RGBW_COLOR,
    ATTR_RGBWW_COLOR,
    ATTR_TRANSITION,
    ATTR_XY_COLOR,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    ColorMode,
    LightEntityFeature,
)
from homeassistant.components.light import (
    DOMAIN as LIGHT_DOMAIN,
)
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError, Unauthorized
from homeassistant.util.color import (
    color_RGB_to_hs,
    color_rgb_to_rgbw,
    color_rgb_to_rgbww,
    color_RGB_to_xy,
)


async def async_apply_scene(
    hass: HomeAssistant,
    scene: dict[str, Any],
    targets: list[str] | None = None,
    context: Context | None = None,
) -> dict[str, Any]:
    """Apply colors sequentially, skipping absent, unavailable or incompatible lights."""
    assignments = scene.get("targets", [])
    selected = list(dict.fromkeys(targets or [item["entity_id"] for item in assignments]))
    if context is not None and context.user_id is not None:
        user = await hass.auth.async_get_user(context.user_id)
        if user is None:
            raise Unauthorized(context=context)
        if not user.is_admin and any(
            not user.permissions.check_entity(entity_id, POLICY_CONTROL) for entity_id in selected
        ):
            raise Unauthorized(context=context)
    by_id = {item["entity_id"]: item for item in assignments}
    results = {"applied": [], "skipped": [], "failed": []}
    for index, entity_id in enumerate(selected):
        state = hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            results["skipped"].append(entity_id)
            continue
        attrs = state.attributes
        modes = set(attrs.get("supported_color_modes", ()))
        assignment = by_id.get(entity_id, {})
        if not assignment.get("enabled", True):
            results["skipped"].append(entity_id)
            continue
        features = attrs.get("supported_features", 0)
        transition = assignment.get("transition", scene.get("transition"))
        transition_payload = (
            {ATTR_TRANSITION: transition}
            if transition and features & LightEntityFeature.TRANSITION
            else {}
        )
        if assignment.get("state", "on") == "off":
            try:
                await hass.services.async_call(
                    LIGHT_DOMAIN,
                    SERVICE_TURN_OFF,
                    {"entity_id": entity_id, **transition_payload},
                    blocking=True,
                    context=context,
                )
            except HomeAssistantError:
                results["failed"].append(entity_id)
            else:
                results["applied"].append(entity_id)
            continue
        mode = assignment.get("color_mode")
        payload: dict[str, Any] = {}
        palette = scene["palette"]
        color_index = assignment.get("color_index", index)
        color = assignment.get("color", palette[color_index % len(palette)])
        rgb = tuple(int(color[offset : offset + 2], 16) for offset in (1, 3, 5))
        if mode is None:
            mode = next(
                (
                    candidate
                    for candidate, color_mode in (
                        ("xy", ColorMode.XY),
                        ("rgb", ColorMode.RGB),
                        ("hs", ColorMode.HS),
                        ("rgbw", ColorMode.RGBW),
                        ("rgbww", ColorMode.RGBWW),
                        ("brightness", ColorMode.BRIGHTNESS),
                        ("none", ColorMode.ONOFF),
                    )
                    if color_mode in modes
                ),
                None,
            )
        if mode == "xy" and ColorMode.XY in modes:
            payload[ATTR_XY_COLOR] = color_RGB_to_xy(*rgb)
        elif mode == "rgb" and ColorMode.RGB in modes:
            payload[ATTR_RGB_COLOR] = rgb
        elif mode == "hs" and ColorMode.HS in modes:
            payload[ATTR_HS_COLOR] = color_RGB_to_hs(*rgb)
        elif mode == "rgbw" and ColorMode.RGBW in modes:
            payload[ATTR_RGBW_COLOR] = color_rgb_to_rgbw(*rgb)
        elif mode == "rgbww" and ColorMode.RGBWW in modes:
            min_kelvin = attrs.get("min_color_temp_kelvin")
            max_kelvin = attrs.get("max_color_temp_kelvin")
            if (
                not isinstance(min_kelvin, int)
                or isinstance(min_kelvin, bool)
                or not isinstance(max_kelvin, int)
                or isinstance(max_kelvin, bool)
                or min_kelvin >= max_kelvin
            ):
                results["skipped"].append(entity_id)
                continue
            payload[ATTR_RGBWW_COLOR] = color_rgb_to_rgbww(*rgb, min_kelvin, max_kelvin)
        elif mode == "color_temp_kelvin" and ColorMode.COLOR_TEMP in modes:
            # This first slice does not guess a white point from a colorful palette.
            kelvin = assignment.get("color_temp_kelvin")
            kelvin_range = attrs.get("min_color_temp_kelvin"), attrs.get("max_color_temp_kelvin")
            if not isinstance(kelvin, int) or not all(isinstance(v, int) for v in kelvin_range):
                results["skipped"].append(entity_id)
                continue
            payload[ATTR_COLOR_TEMP_KELVIN] = min(kelvin_range[1], max(kelvin_range[0], kelvin))
        elif mode in ("brightness", "none"):
            pass
        else:
            results["skipped"].append(entity_id)
            continue
        brightness = assignment.get("brightness_pct", scene.get("brightness_pct"))
        if brightness is not None and any(m != ColorMode.ONOFF for m in modes):
            payload[ATTR_BRIGHTNESS_PCT] = brightness
        payload.update(transition_payload)
        try:
            await hass.services.async_call(
                LIGHT_DOMAIN,
                SERVICE_TURN_ON,
                {"entity_id": entity_id, **payload},
                blocking=True,
                context=context,
            )
        except HomeAssistantError:
            results["failed"].append(entity_id)
        else:
            results["applied"].append(entity_id)
    return results
