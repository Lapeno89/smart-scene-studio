"""Scene schema tests."""

from copy import deepcopy
from uuid import uuid4

import pytest

from custom_components.smart_scene_studio.models import scene_object_id, validate_scene


def scene() -> dict:
    return {
        "id": str(uuid4()),
        "name": "Calm Night",
        "kind": "static",
        "palette": ["#123456", "#abcdef"],
        "targets": [{"entity_id": "light.desk", "color_index": 0}],
    }


def test_scene_identity_survives_rename() -> None:
    original = validate_scene(scene())
    renamed_input = deepcopy(original)
    renamed_input["name"] = "New Scene Name"
    renamed = validate_scene(renamed_input)
    assert renamed["id"] == original["id"]
    assert scene_object_id(renamed) != scene_object_id(original)


@pytest.mark.parametrize("palette", [[], ["#000000"], ["red", "#ffffff"], ["#000000"] * 9])
def test_rejects_invalid_palette(palette: list[str]) -> None:
    value = scene()
    value["palette"] = palette
    with pytest.raises(ValueError):
        validate_scene(value)
