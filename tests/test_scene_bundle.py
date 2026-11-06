"""Portable scene JSON bundle validation and import planning tests."""

from uuid import uuid4

import pytest

from custom_components.smart_scene_studio.scene_bundle import (
    BUNDLE_FORMAT,
    BUNDLE_VERSION,
    create_export_bundle,
    plan_scene_import,
)


def scene(*, name="Portable scene", scene_id=None, target="light.source"):
    return {
        "id": scene_id or str(uuid4()),
        "name": name,
        "kind": "static",
        "palette": ["#112233", "#445566"],
        "targets": [{"entity_id": target, "enabled": True}],
    }


def bundle(*scenes):
    return {"format": BUNDLE_FORMAT, "version": BUNDLE_VERSION, "scenes": list(scenes)}


def test_export_is_allowlisted_and_preserves_scene_provenance():
    builtin = {**scene(name="Preset"), "api_token": "must not leak"}
    user_scene = {**scene(name="User"), "private_data": {"key": "secret"}}

    exported = create_export_bundle([builtin], (user_scene,))

    assert exported["format"] == BUNDLE_FORMAT
    assert exported["version"] == BUNDLE_VERSION
    assert [item["provenance"] for item in exported["scenes"]] == ["builtin", "user"]
    assert "api_token" not in exported["scenes"][0]
    assert "private_data" not in exported["scenes"][1]


def test_import_maps_explicitly_and_disables_unmapped_targets():
    source = scene()
    source["targets"].append({"entity_id": "light.unavailable", "color_index": 1})

    plan = plan_scene_import(
        bundle(source),
        {"light.source": "light.destination"},
        (),
        [],
        now="2026-01-01T00:00:00+00:00",
    )

    assert plan["scenes"][0]["targets"] == [
        {"entity_id": "light.destination", "enabled": True, "color_index": 0, "state": "on"},
        {"entity_id": "light.unavailable", "enabled": False, "color_index": 1, "state": "on"},
    ]
    assert plan["unmapped_targets"] == ["light.unavailable"]
    assert plan["items"][0]["identity"] == "preserved"


def test_import_is_idempotent_and_derives_id_on_uuid_collision():
    source = scene()
    first = plan_scene_import(bundle(source), {}, (), [], now="2026-01-01T00:00:00+00:00")
    duplicate = plan_scene_import(
        bundle(source), {}, tuple(first["scenes"]), [], now="2026-02-01T00:00:00+00:00"
    )
    changed = {**source, "name": "Renamed content"}
    collision_a = plan_scene_import(
        bundle(changed), {}, (source,), [], now="2026-01-01T00:00:00+00:00"
    )
    collision_b = plan_scene_import(
        bundle(changed), {}, (source,), [], now="2026-01-01T00:00:00+00:00"
    )

    assert duplicate["imported_count"] == 0
    assert duplicate["skipped_count"] == 1
    assert collision_a["scenes"][0]["id"] != source["id"]
    assert collision_a["scenes"][0]["id"] == collision_b["scenes"][0]["id"]
    assert collision_a["items"][0]["identity"] == "derived"


def test_import_rejects_mapping_collisions_within_a_scene():
    source = scene()
    source["targets"].append({"entity_id": "light.second"})

    with pytest.raises(ValueError, match="Multiple targets.*map to light.destination"):
        plan_scene_import(
            bundle(source),
            {
                "light.source": "light.destination",
                "light.second": "light.destination",
            },
            (),
            [],
        )


def test_identical_duplicate_source_uuids_import_once():
    source = scene()
    duplicated = {**source, "targets": [dict(target) for target in source["targets"]]}

    plan = plan_scene_import(bundle(source, duplicated), {}, (), [])

    assert plan["imported_count"] == 1
    assert plan["skipped_count"] == 1
    assert plan["items"][0]["scene_id"] == plan["items"][1]["scene_id"]
    assert plan["items"][1]["action"] == "skip_duplicate"


def test_conflicting_definitions_with_duplicate_source_uuid_are_rejected():
    source = scene(name="First")
    conflict = {**source, "name": "Second"}

    with pytest.raises(ValueError, match="Conflicting scene definitions share source UUID"):
        plan_scene_import(bundle(source, conflict), {}, (), [])


@pytest.mark.parametrize(
    "invalid_bundle, mappings, message",
    [
        (
            {"format": BUNDLE_FORMAT, "version": 99, "scenes": []},
            {},
            "Unsupported scene bundle version",
        ),
        (
            {"format": BUNDLE_FORMAT, "version": BUNDLE_VERSION, "scenes": [{"unknown": 1}]},
            {},
            "Unsupported bundled scene fields",
        ),
        (bundle(scene()), {"light.unknown": "light.target"}, "do not match bundled lights"),
        (bundle(scene()), {"light.source": "switch.target"}, "valid light entity IDs"),
    ],
)
def test_import_rejects_unsupported_schema_and_invalid_mappings(invalid_bundle, mappings, message):
    with pytest.raises(ValueError, match=message):
        plan_scene_import(invalid_bundle, mappings, (), [])

