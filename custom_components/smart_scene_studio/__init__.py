"""Smart Scene Studio integration lifecycle."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    DATA_PRESETS,
    DATA_REPOSITORY,
    DATA_SCENE_ENTITIES,
    DOMAIN,
    PLATFORMS,
    SERVICE_APPLY_SCENE,
)
from .light_control import async_apply_scene
from .repository import SceneRepository, UnsupportedStorageVersion
from .websocket_api import async_load_presets
from .websocket_api import async_setup as async_setup_websocket_api

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Register validated scene activation service."""
    presets = await async_load_presets(hass)
    hass.data.setdefault(DOMAIN, {})[DATA_PRESETS] = presets
    async_setup_websocket_api(hass)

    async def handle_apply_scene(call: ServiceCall) -> dict[str, Any] | None:
        """Apply an immutable builtin or saved scene to explicitly selected lights."""
        scene_id = call.data["scene_id"]
        targets = call.data["entity_id"]
        scene = None
        for entry_data in hass.data.get(DOMAIN, {}).values():
            repository = entry_data.get(DATA_REPOSITORY) if isinstance(entry_data, dict) else None
            if repository:
                scene = next((item for item in repository.scenes if item["id"] == scene_id), None)
                break
        if scene is None:
            scene = next((item for item in presets if item["id"] == scene_id), None)
        if scene is None:
            raise HomeAssistantError("Unknown Smart Scene Studio scene")
        result = await async_apply_scene(hass, scene, targets, context=call.context)
        return result if call.return_response else None

    hass.services.async_register(
        DOMAIN,
        SERVICE_APPLY_SCENE,
        handle_apply_scene,
        schema=vol.Schema(
            {
                vol.Required("scene_id"): str,
                vol.Required("entity_id"): vol.All(
                    cv.ensure_list, [cv.entity_id], vol.Length(min=1, max=64)
                ),
            }
        ),
        supports_response=SupportsResponse.OPTIONAL,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialize storage and platforms."""
    repository = SceneRepository(hass)
    try:
        await repository.async_load()
    except UnsupportedStorageVersion:
        # Keep the entry loadable and never overwrite storage we cannot interpret.
        raise
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {DATA_REPOSITORY: repository}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload platforms and release entry data."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    hass.data[DOMAIN].pop(entry.entry_id, None)
    hass.data[DOMAIN].pop(DATA_SCENE_ENTITIES, None)
    return True
