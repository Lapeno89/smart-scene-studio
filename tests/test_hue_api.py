"""WebSocket Hue V2 import tests with a fully simulated bridge runtime."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.components.light import ColorMode
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.smart_scene_studio.const import DATA_REPOSITORY, DOMAIN
from tests.test_integration import add_entry

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")
FIXTURES = Path(__file__).parent / "fixtures" / "hue_v2"
BRIDGE_ID = "fixture-bridge-uuid"
COLOR_ID = "11111111-1111-4111-8111-111111111111"
WHITE_ID = "22222222-2222-4222-8222-222222222222"
UNMAPPED_ID = "33333333-3333-4333-8333-333333333333"
SCENE_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


async def request(client, payload):
    await client.send_json_auto_id(payload)
    return await client.receive_json()


def fake_hue_api():
    api = SimpleNamespace(
        config=SimpleNamespace(bridge_id=BRIDGE_ID),
        scenes=fixture("scenes.json"),
        lights=fixture("lights.json"),
        rooms=fixture("groups.json"),
        zones=[],
        fetch_full_state=AsyncMock(),
    )
    bridge = SimpleNamespace(api=api, api_version=2)
    return SimpleNamespace(runtime_data=bridge), api


async def test_hue_v2_list_preview_import_and_deferred_remap_are_local(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use only JSON fixture resources and the stubbed Home Assistant runtime."""
    await add_entry(hass)
    hue_entry, api = fake_hue_api()
    monkeypatch.setattr(hass.config_entries, "async_loaded_entries", lambda domain: [hue_entry])
    hass.states.async_set(
        "light.fixture_color",
        "off",
        {"supported_color_modes": {ColorMode.XY}},
    )
    hass.states.async_set(
        "light.fixture_white",
        "off",
        {
            "supported_color_modes": {ColorMode.COLOR_TEMP},
            "min_color_temp_kelvin": 2000,
            "max_color_temp_kelvin": 6500,
        },
    )
    hass.states.async_set(
        "light.fixture_unmapped",
        "off",
        {"supported_color_modes": {ColorMode.BRIGHTNESS}},
    )
    client = await hass_ws_client(hass)

    listing = await request(
        client,
        {"type": f"{DOMAIN}/hue/list", "bridge_id": BRIDGE_ID},
    )
    assert listing["success"]
    assert listing["result"]["scenes"][0]["name"] == "Fixture Mixed Scene"
    assert listing["result"]["target_lights"][0]["entity_id"].startswith("light.")
    assert "api_key" not in json.dumps(listing).casefold()
    api.fetch_full_state.assert_not_awaited()

    mapping = {COLOR_ID: "light.fixture_color", WHITE_ID: "light.fixture_white"}
    preview = await request(
        client,
        {
            "type": f"{DOMAIN}/hue/import",
            "bridge_id": BRIDGE_ID,
            "dry_run": True,
            "scene_ids": [SCENE_ID],
            "target_mappings": mapping,
        },
    )
    assert preview["success"]
    report = preview["result"]["report"]
    assert report["imported_count"] == 1
    assert report["capacity"]["can_commit"]
    assert report["conversion"]["unmapped_light_ids"] == [UNMAPPED_ID]
    repository = next(
        data[DATA_REPOSITORY]
        for data in hass.data[DOMAIN].values()
        if isinstance(data, dict) and DATA_REPOSITORY in data
    )
    assert repository.scenes == ()

    committed = await request(
        client,
        {
            "type": f"{DOMAIN}/hue/import",
            "bridge_id": BRIDGE_ID,
            "dry_run": False,
            "scene_ids": [SCENE_ID],
            "target_mappings": mapping,
        },
    )
    assert committed["success"]
    imported = committed["result"]["report"]["scenes"][0]
    assert imported["source_provenance"] == "hue_import"
    scene_id = imported["scene_id"]
    scene = next(
        scene
        for data in hass.data[DOMAIN].values()
        if isinstance(data, dict) and DATA_REPOSITORY in data
        for scene in data[DATA_REPOSITORY].scenes
        if scene["id"] == scene_id
    )
    original_palette = list(scene["palette"])
    assert scene["source"]["id"] == SCENE_ID
    manager = next(
        data["scene_manager"]
        for data in hass.data[DOMAIN].values()
        if isinstance(data, dict) and "scene_manager" in data
    )
    turn_on = AsyncMock()
    turn_off = AsyncMock()
    hass.services.async_register("light", "turn_on", turn_on)
    hass.services.async_register("light", "turn_off", turn_off)
    await manager.entities[scene_id].async_activate()
    xy_calls = [
        call
        for call in turn_on.await_args_list
        if call.args[0].data.get("entity_id") == "light.fixture_color"
    ]
    assert xy_calls[0].args[0].data["xy_color"] == (0.32, 0.33)

    remapped = await request(
        client,
        {
            "type": f"{DOMAIN}/hue/remap",
            "scene_id": scene_id,
            "target_mappings": {
                **mapping,
                UNMAPPED_ID: "light.fixture_unmapped",
            },
        },
    )
    assert remapped["success"]
    assert remapped["result"]["scene"]["palette"] == original_palette
    assert remapped["result"]["scene"]["source"]["unmapped_light_ids"] == []
    assert api.fetch_full_state.await_count == 2  # preview and commit; list/remap stay local


async def test_hue_import_requires_loaded_v2_entry(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, monkeypatch: pytest.MonkeyPatch
) -> None:
    await add_entry(hass)
    v1_entry = SimpleNamespace(runtime_data=SimpleNamespace(api=object(), api_version=1))
    monkeypatch.setattr(hass.config_entries, "async_loaded_entries", lambda domain: [v1_entry])
    client = await hass_ws_client(hass)

    response = await request(
        client,
        {
            "type": f"{DOMAIN}/hue/import",
            "bridge_id": BRIDGE_ID,
            "dry_run": True,
        },
    )

    assert not response["success"]
    assert "Hue Bridge V2" in response["error"]["message"]
