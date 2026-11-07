"""Register the packaged Smart Scene Studio Home Assistant panel."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.panel_custom import async_register_panel
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DATA_FRONTEND_ASSETS_REGISTERED,
    DATA_FRONTEND_PANEL_ENTRY,
    DOMAIN,
)

PANEL_URL_PATH = "smart-scene-studio"
PANEL_ELEMENT = "smart-scene-studio-panel"
PANEL_ASSET_URL = "/api/smart_scene_studio/frontend/smart-scene-studio.js"
PANEL_ASSET_VERSION = "0.1.0-ui001"
PANEL_ASSET_PATH = Path(__file__).parent / "frontend" / "dist" / "smart-scene-studio.js"


async def async_register_frontend(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register static assets once per process and the panel once per entry load."""
    domain_data = hass.data[DOMAIN]
    if not await hass.async_add_executor_job(PANEL_ASSET_PATH.is_file):
        raise HomeAssistantError(f"Packaged panel asset is missing: {PANEL_ASSET_PATH.name}")

    if not domain_data.get(DATA_FRONTEND_ASSETS_REGISTERED):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(PANEL_ASSET_URL, str(PANEL_ASSET_PATH), cache_headers=True)]
        )
        domain_data[DATA_FRONTEND_ASSETS_REGISTERED] = True

    if frontend.async_panel_exists(hass, PANEL_URL_PATH):
        if domain_data.get(DATA_FRONTEND_PANEL_ENTRY) == entry.entry_id:
            return
        raise HomeAssistantError(f"Home Assistant panel path {PANEL_URL_PATH!r} is already in use")

    await async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_ELEMENT,
        sidebar_title="Smart Scene Studio",
        sidebar_icon="mdi:palette",
        module_url=f"{PANEL_ASSET_URL}?v={PANEL_ASSET_VERSION}",
        require_admin=False,
        trust_external=False,
    )
    domain_data[DATA_FRONTEND_PANEL_ENTRY] = entry.entry_id


def async_unregister_frontend(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the sidebar panel on unload; the public static bundle route is process-wide."""
    domain_data = hass.data.get(DOMAIN, {})
    if domain_data.get(DATA_FRONTEND_PANEL_ENTRY) != entry.entry_id:
        return
    frontend.async_remove_panel(hass, PANEL_URL_PATH)
    domain_data.pop(DATA_FRONTEND_PANEL_ENTRY, None)
