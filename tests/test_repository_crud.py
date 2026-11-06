"""Repository mutation safety tests."""

import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from custom_components.smart_scene_studio.repository import SceneRepository


def scene(name: str) -> dict:
    return {
        "id": str(uuid4()),
        "name": name,
        "kind": "static",
        "palette": ["#112233", "#445566"],
        "targets": [],
    }


async def test_concurrent_scene_creates_keep_every_successful_write(hass) -> None:
    """The async lock prevents concurrent writes from losing updates."""
    repository = SceneRepository(hass)

    await asyncio.gather(
        repository.async_save_scene(scene("First")),
        repository.async_save_scene(scene("Second")),
        repository.async_save_scene(scene("Third")),
    )

    assert {item["name"] for item in repository.scenes} == {"First", "Second", "Third"}


async def test_failed_store_write_does_not_publish_candidate_in_memory(hass, monkeypatch) -> None:
    """A failed persistent write leaves the visible repository unchanged."""
    repository = SceneRepository(hass)
    original = await repository.async_save_scene(scene("Original"))
    monkeypatch.setattr(
        repository._store,
        "async_save",
        AsyncMock(side_effect=OSError("simulated disk failure")),
    )

    with pytest.raises(OSError, match="simulated disk failure"):
        await repository.async_update_scene(original["id"], {"name": "Uncommitted"})

    assert repository.scenes[0]["name"] == "Original"


async def test_concurrent_update_and_delete_leave_store_and_memory_consistent(hass) -> None:
    """Racing an update and delete cannot resurrect a deleted scene."""
    repository = SceneRepository(hass)
    original = await repository.async_save_scene(scene("Race"))

    results = await asyncio.gather(
        repository.async_update_scene(original["id"], {"name": "Updated race"}),
        repository.async_delete_scene(original["id"]),
        return_exceptions=True,
    )

    assert any(result is None for result in results)
    assert not repository.scenes
    reloaded = SceneRepository(hass)
    await reloaded.async_load()
    assert not reloaded.scenes


async def test_storage_limits_reject_before_writing(hass, monkeypatch) -> None:
    """Scene count and serialized-size limits preserve current storage."""
    repository = SceneRepository(hass)
    save = AsyncMock()
    monkeypatch.setattr(repository._store, "async_save", save)

    with pytest.raises(ValueError, match="500 user scenes"):
        await repository._async_save_candidate({str(index): {} for index in range(501)})
    with pytest.raises(ValueError, match="1 MiB"):
        await repository._async_save_candidate({"large": {"payload": "x" * (1_048_576 + 1)}})

    save.assert_not_awaited()
    assert not repository.scenes


async def test_pr001_v1_storage_loads_without_changing_scene_identity(hass, monkeypatch) -> None:
    """The PR-001 schema-v1 envelope remains readable by the CRUD repository."""
    legacy = scene("Persisted before CRUD")
    repository = SceneRepository(hass)
    monkeypatch.setattr(
        repository._store,
        "async_load",
        AsyncMock(return_value={"schema_version": 1, "scenes": [legacy]}),
    )

    await repository.async_load()

    assert repository.scenes[0]["id"] == legacy["id"]
    assert repository.scenes[0]["name"] == "Persisted before CRUD"


async def test_malformed_storage_version_is_rejected_without_write(hass, monkeypatch) -> None:
    """Malformed storage metadata cannot trigger an implicit empty-store save."""
    repository = SceneRepository(hass)
    save = AsyncMock()
    monkeypatch.setattr(
        repository._store,
        "async_load",
        AsyncMock(return_value={"schema_version": "2", "scenes": []}),
    )
    monkeypatch.setattr(repository._store, "async_save", save)

    with pytest.raises(ValueError, match="Invalid Smart Scene Studio storage envelope"):
        await repository.async_load()

    save.assert_not_awaited()
