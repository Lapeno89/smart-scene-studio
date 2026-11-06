"""Original preset library regression tests."""

import json
from pathlib import Path

from custom_components.smart_scene_studio.models import validate_scene


def test_original_presets_are_unique_targetless_and_cover_requested_families():
    path = (
        Path(__file__).parents[1]
        / "custom_components"
        / "smart_scene_studio"
        / "presets.json"
    )
    presets = [validate_scene(item) for item in json.loads(path.read_text(encoding="utf-8"))]

    assert len(presets) == 11
    assert len({preset["id"] for preset in presets}) == len(presets)
    assert all(not preset["targets"] for preset in presets)
    assert {
        "ambient",
        "relax",
        "focus",
        "warm_evening",
        "ocean",
        "forest",
        "sunset",
        "white",
    } <= {preset["category"] for preset in presets}
    assert {
        preset["white_temperature_kelvin"]
        for preset in presets
        if preset["category"] == "white"
    } == {2700, 4000}
