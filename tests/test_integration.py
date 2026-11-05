"""Home Assistant integration behavior tests; all light calls are stubbed."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from homeassistant.components.light import ColorMode, LightEntityFeature
from homeassistant.config_entries import SOURCE_USER
from homeassistant.exceptions import HomeAssistantError

from custom_components.smart_scene_studio.const import DOMAIN
from custom_components.smart_scene_studio.repository import (
    SceneRepository,
    UnsupportedStorageVersion,
)

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def add_entry(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] == "create_entry"
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_config_flow_and_clean_unload(hass) -> None:
    entry = await add_entry(hass)
    assert len(hass.data[DOMAIN]["scene_entities"]) == 3
    assert hass.states.get("scene.amber_evening") is not None
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("scene.amber_evening") is None


async def test_service_skips_unsupported_and_unavailable(hass) -> None:
    await add_entry(hass)
    light_calls = AsyncMock()
    hass.services.async_register("light", "turn_on", light_calls)
    hass.states.async_set(
        "light.rgb", "off", {"supported_color_modes": [ColorMode.RGB], "supported_features": 0}
    )
    hass.states.async_set(
        "light.xy", "off", {"supported_color_modes": [ColorMode.XY], "supported_features": 0}
    )
    hass.states.async_set(
        "light.white",
        "off",
        {"supported_color_modes": [ColorMode.COLOR_TEMP], "supported_features": 0},
    )
    hass.states.async_set(
        "light.offline", "unavailable", {"supported_color_modes": [ColorMode.RGB]}
    )
    result = await hass.services.async_call(
        DOMAIN,
        "apply_scene",
        {
            "scene_id": "b88ea8a1-0db4-4df5-9e91-4d93a3d30001",
            "entity_id": ["light.rgb", "light.xy", "light.white", "light.offline", "light.missing"],
        },
        blocking=True,
        return_response=True,
    )
    assert light_calls.await_count == 2
    payloads = [call.args[0].data for call in light_calls.await_args_list]
    assert payloads[0]["entity_id"] == "light.rgb"
    assert "rgb_color" in payloads[0]
    assert payloads[1]["entity_id"] == "light.xy"
    assert "xy_color" in payloads[1]
    assert all("color_temp_kelvin" not in payload for payload in payloads)
    assert all("transition" not in payload for payload in payloads)
    assert result["skipped"] == ["light.white", "light.offline", "light.missing"]


async def test_one_light_failure_is_partial(hass) -> None:
    await add_entry(hass)

    async def turn_on(call):
        if call.data["entity_id"] == "light.bad":
            raise HomeAssistantError("simulated failure")

    hass.services.async_register("light", "turn_on", turn_on)
    for entity_id in ("light.bad", "light.good"):
        hass.states.async_set(entity_id, "off", {"supported_color_modes": [ColorMode.RGB]})
    result = await hass.services.async_call(
        DOMAIN,
        "apply_scene",
        {
            "scene_id": "b88ea8a1-0db4-4df5-9e91-4d93a3d30001",
            "entity_id": ["light.bad", "light.good"],
        },
        blocking=True,
        return_response=True,
    )
    assert result["failed"] == ["light.bad"]
    assert result["applied"] == ["light.good"]


async def test_saved_scene_entity_appears_after_reload(hass) -> None:
    entry = await add_entry(hass)
    repository = hass.data[DOMAIN][entry.entry_id]["repository"]
    scene_id = str(uuid4())
    await repository.async_save_scene(
        {
            "id": scene_id,
            "name": "Persisted",
            "kind": "static",
            "palette": ["#112233", "#445566"],
            "targets": [],
        }
    )
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entity = hass.states.get("scene.persisted")
    assert entity is not None
    scene_entities = hass.data[DOMAIN]["scene_entities"]
    assert scene_entities[scene_id].unique_id == scene_id
    assert hass.data[DOMAIN][entry.entry_id]["repository"].scenes[0]["id"] == scene_id


async def test_store_persists_scene_identity(hass) -> None:
    repository = SceneRepository(hass)
    scene_id = str(uuid4())
    scene = {
        "id": scene_id,
        "name": "Saved",
        "kind": "static",
        "palette": ["#010203", "#AABBCC"],
        "targets": [],
    }
    await repository.async_save_scene(scene)
    reloaded = SceneRepository(hass)
    await reloaded.async_load()
    renamed = dict(reloaded.scenes[0], name="Renamed")
    await reloaded.async_save_scene(renamed)
    final = SceneRepository(hass)
    await final.async_load()
    assert final.scenes[0]["id"] == scene_id
    assert final.scenes[0]["name"] == "Renamed"


async def test_color_modes_and_brightness_payloads(hass) -> None:
    await add_entry(hass)
    light_calls = AsyncMock()
    hass.services.async_register("light", "turn_on", light_calls)
    states = {
        "light.hs": {"supported_color_modes": [ColorMode.HS]},
        "light.rgbw": {"supported_color_modes": [ColorMode.RGBW]},
        "light.rgbww": {
            "supported_color_modes": [ColorMode.RGBWW],
            "min_color_temp_kelvin": 2000,
            "max_color_temp_kelvin": 6500,
        },
        "light.brightness": {"supported_color_modes": [ColorMode.BRIGHTNESS]},
    }
    for entity_id, attrs in states.items():
        hass.states.async_set(entity_id, "off", attrs)
    result = await hass.services.async_call(
        DOMAIN,
        "apply_scene",
        {
            "scene_id": "b88ea8a1-0db4-4df5-9e91-4d93a3d30001",
            "entity_id": list(states),
        },
        blocking=True,
        return_response=True,
    )
    assert result["applied"] == list(states)
    payloads = {
        call.args[0].data["entity_id"]: call.args[0].data for call in light_calls.await_args_list
    }
    assert "hs_color" in payloads["light.hs"]
    assert "rgbw_color" in payloads["light.rgbw"]
    assert "rgbww_color" in payloads["light.rgbww"]
    assert set(payloads["light.brightness"]) == {"entity_id", "brightness_pct"}


async def test_off_and_disabled_target_intentions(hass) -> None:
    entry = await add_entry(hass)
    repository = hass.data[DOMAIN][entry.entry_id]["repository"]
    scene_id = str(uuid4())
    await repository.async_save_scene(
        {
            "id": scene_id,
            "name": "Off intents",
            "kind": "static",
            "palette": ["#112233", "#445566"],
            "targets": [
                {
                    "entity_id": "light.off",
                    "state": "off",
                    "transition": 2,
                },
                {"entity_id": "light.disabled", "enabled": False},
            ],
        }
    )
    turn_off = AsyncMock()
    turn_on = AsyncMock()
    hass.services.async_register("light", "turn_off", turn_off)
    hass.services.async_register("light", "turn_on", turn_on)
    for entity_id in ("light.off", "light.disabled"):
        hass.states.async_set(
            entity_id,
            "on",
            {
                "supported_color_modes": [ColorMode.RGB],
                "supported_features": LightEntityFeature.TRANSITION,
            },
        )
    result = await hass.services.async_call(
        DOMAIN,
        "apply_scene",
        {"scene_id": scene_id, "entity_id": ["light.off", "light.disabled"]},
        blocking=True,
        return_response=True,
    )
    assert result["applied"] == ["light.off"]
    assert result["skipped"] == ["light.disabled"]
    assert turn_off.await_args.args[0].data == {
        "entity_id": "light.off",
        "transition": 2,
    }
    turn_on.assert_not_awaited()


async def test_newer_storage_version_is_read_only(hass, monkeypatch) -> None:
    repository = SceneRepository(hass)
    monkeypatch.setattr(
        repository._store, "async_load", AsyncMock(return_value={"schema_version": 2, "scenes": []})
    )
    with pytest.raises(UnsupportedStorageVersion, match="Unsupported scene storage version"):
        await repository.async_load()
    with pytest.raises(UnsupportedStorageVersion, match="read-only"):
        await repository.async_save_scene(
            {
                "id": str(uuid4()),
                "name": "No overwrite",
                "kind": "static",
                "palette": ["#010203", "#AABBCC"],
                "targets": [],
            }
        )
