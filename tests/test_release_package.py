"""Release ZIP regression tests."""

from __future__ import annotations

import hashlib
import json
import zipfile

from scripts.build_release_zip import build_release_zip


def test_alpha_release_archive_is_complete_safe_and_reproducible(tmp_path) -> None:
    """The exact committed integration bundle can be installed without build tooling."""
    first_path, commit, file_count, digest = build_release_zip(tmp_path / "first.zip")
    second_path, second_commit, second_count, second_digest = build_release_zip(
        tmp_path / "second.zip"
    )

    assert second_commit == commit
    assert second_count == file_count
    assert second_digest == digest
    assert hashlib.sha256(first_path.read_bytes()).hexdigest() == digest
    assert first_path.read_bytes() == second_path.read_bytes()

    with zipfile.ZipFile(first_path) as archive:
        names = set(archive.namelist())
        assert "custom_components/smart_scene_studio/manifest.json" in names
        assert "custom_components/smart_scene_studio/__init__.py" in names
        assert "custom_components/smart_scene_studio/config_flow.py" in names
        assert "custom_components/smart_scene_studio/scene.py" in names
        assert "custom_components/smart_scene_studio/presets.json" in names
        assert "custom_components/smart_scene_studio/websocket_api.py" in names
        assert "custom_components/smart_scene_studio/frontend/dist/smart-scene-studio.js" in names
        assert "custom_components/smart_scene_studio/translations/en.json" in names
        assert "LICENSE" in names
        manifest = json.loads(archive.read("custom_components/smart_scene_studio/manifest.json"))
        presets = json.loads(archive.read("custom_components/smart_scene_studio/presets.json"))
        candidate = json.loads(archive.read("RELEASE_CANDIDATE.json"))
        assert manifest["version"] == "0.1.0-alpha.1"
        assert candidate["candidate_tag"] == "v0.1.0-alpha.1"
        assert candidate["source_commit"] == commit
        assert len(presets) == 11
        assert all("node_modules" not in name and "__pycache__" not in name for name in names)
        assert not any(name.startswith("tests/") for name in names)
