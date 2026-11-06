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
