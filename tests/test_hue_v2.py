"""Offline Hue API V2 resource conversion tests."""

import json
from pathlib import Path

import pytest
from homeassistant.components.light import ColorMode

from custom_components.smart_scene_studio.hue_v2 import (
    convert_hue_v2_resources,
    plan_hue_scene_import,
    remap_hue_scene_targets,
)

FIXTURES = Path(__file__).parent / "fixtures" / "hue_v2"
BRIDGE_ID = "fixture-bridge-uuid"
COLOR_ID = "11111111-1111-4111-8111-111111111111"
WHITE_ID = "22222222-2222-4222-8222-222222222222"
UNMAPPED_ID = "33333333-3333-4333-8333-333333333333"
SCENE_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def convert(mappings=None, available=None):
    return convert_hue_v2_resources(
        fixture("scenes.json"),
        fixture("lights.json"),
        fixture("groups.json"),
        BRIDGE_ID,
        mappings or {},
        available_targets=available or {},
    )


def test_converts_xy_and_mirek_and_preserves_bridge_source_identity():
    scenes, report = convert(
        {COLOR_ID: "light.fixture_color", WHITE_ID: "light.fixture_white"},
        {
            "light.fixture_color": {"supported_color_modes": {ColorMode.XY}},
            "light.fixture_white": {
                "supported_color_modes": {ColorMode.COLOR_TEMP},
                "min_color_temp_kelvin": 2000,
                "max_color_temp_kelvin": 6500,
            },
        },
    )

    scene = scenes[0]
    by_id = {target["source_id"]: target for target in scene["targets"]}
    assert scene["source"]["id"] == SCENE_ID
    assert scene["source"]["bridge_id"] == BRIDGE_ID
    assert scene["source"]["group_name"] == "Fixture Room"
    assert by_id[COLOR_ID]["color_xy"] == [0.32, 0.33]
    assert by_id[COLOR_ID]["color_mode"] == "xy"
    assert "target_color_gamut_not_verified" in scene["source"]["unsupported_features"]
    assert by_id[WHITE_ID]["color_temp_kelvin"] == 4000
    assert UNMAPPED_ID in report["unmapped_light_ids"]
    assert scene["source"]["source_actions"][-1]["on"] is False


def test_does_not_guess_unmapped_lights_and_flags_dynamic_gradient_features():
    scenes, report = convert()

    assert all(
        target["entity_id"].startswith("light.") for item in scenes for target in item["targets"]
    )
    assert scenes[0]["targets"] == []
    dynamic = scenes[1]
    assert "auto_dynamic" in dynamic["source"]["unsupported_features"]
    assert "dynamic_palette" in dynamic["source"]["unsupported_features"]
    assert "gradient" in dynamic["source"]["unsupported_features"]
    assert set(report["unmapped_light_ids"]) == {
        COLOR_ID,
        UNMAPPED_ID,
        WHITE_ID,
        "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
    }
    assert "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee" in report["missing_light_ids"]


def test_unavailable_or_unsupported_destination_is_disabled_and_reported():
    scenes, report = convert(
        {COLOR_ID: "light.no_color", WHITE_ID: "light.offline"},
        {
            "light.no_color": {"supported_color_modes": {ColorMode.BRIGHTNESS}},
        },
    )
    targets = {target["entity_id"]: target for target in scenes[0]["targets"]}

    assert not targets["light.no_color"]["enabled"]
    assert not targets["light.offline"]["enabled"]
    assert "mapped_target_does_not_support_xy" in report["unsupported_features"]
    assert "mapped_target_unavailable" in report["unsupported_features"]
    assert WHITE_ID in report["missing_light_ids"]


def test_reimport_is_idempotent_per_bridge_and_keeps_same_scene_from_other_bridge():
    scenes, _ = convert()
    first = plan_hue_scene_import(scenes, (), [])
    repeated = plan_hue_scene_import(scenes, tuple(first["scenes"]), [])
    second_bridge, _ = convert_hue_v2_resources(
        fixture("scenes.json"),
        fixture("lights.json"),
        fixture("groups.json"),
        "another-fixture-bridge",
        {},
    )
    independent = plan_hue_scene_import(second_bridge, tuple(first["scenes"]), [])

    assert first["imported_count"] == 3
    assert repeated["imported_count"] == 0
    assert repeated["skipped_count"] == 3
    assert independent["imported_count"] == 3
    assert scenes[0]["id"] != second_bridge[0]["id"]


def test_deferred_mapping_preserves_palette_and_original_light_ids():
    scenes, _ = convert()
    imported = scenes[0]
    palette = list(imported["palette"])
    remapped = remap_hue_scene_targets(
        imported,
        {
            COLOR_ID: "light.new_color",
            WHITE_ID: "light.new_white",
        },
        available_targets={
            "light.new_color": {"supported_color_modes": {ColorMode.XY}},
            "light.new_white": {
                "supported_color_modes": {ColorMode.COLOR_TEMP},
                "min_color_temp_kelvin": 2000,
                "max_color_temp_kelvin": 6500,
            },
        },
    )

    assert remapped["palette"] == palette
    assert {target["source_id"] for target in remapped["targets"]} == {COLOR_ID, WHITE_ID}
    assert remapped["source"]["unmapped_light_ids"] == [UNMAPPED_ID]


def test_rejects_invalid_mappings_duplicate_scene_ids_and_oversized_snapshot():
    with pytest.raises(ValueError, match="valid light"):
        convert({COLOR_ID: "switch.fixture"})
    scenes = fixture("scenes.json")
    with pytest.raises(ValueError, match="Duplicate Hue scene ID"):
        convert_hue_v2_resources(
            [scenes[0], scenes[0]], fixture("lights.json"), fixture("groups.json"), BRIDGE_ID, {}
        )
    with pytest.raises(ValueError, match="4 MiB"):
        convert_hue_v2_resources(
            [{**scenes[0], "padding": "x" * (4 * 1024 * 1024)}],
            fixture("lights.json"),
            fixture("groups.json"),
            BRIDGE_ID,
            {},
        )
