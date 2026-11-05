"""Versioned Home Assistant Store-backed scene repository."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_MINOR_VERSION, STORAGE_VERSION
from .models import validate_scene


class UnsupportedStorageVersion(Exception):
    """Stored scene data is newer than this integration understands."""


class SceneRepository:
    """Persist only validated user-authored scenes."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY, minor_version=STORAGE_MINOR_VERSION
        )
        self._scenes: dict[str, dict[str, Any]] = {}
        self._read_only = False

    @property
    def scenes(self) -> tuple[dict[str, Any], ...]:
        """Return scenes in deterministic insertion order."""
        return tuple(self._scenes.values())

    async def async_load(self) -> None:
        """Load supported data; never replace a future schema with empty data."""
        raw = await self._store.async_load()
        if raw is None:
            return
        if (
            not isinstance(raw, dict)
            or not isinstance(raw.get("schema_version"), int)
            or isinstance(raw.get("schema_version"), bool)
        ):
            raise ValueError("Invalid Smart Scene Studio storage envelope")
        version = raw["schema_version"]
        if version > STORAGE_VERSION:
            self._read_only = True
            raise UnsupportedStorageVersion(f"Unsupported scene storage version {version}")
        if version < STORAGE_VERSION:
            raw = await self.async_migrate(raw, version)
            await self._store.async_save(raw)
        scenes = raw.get("scenes")
        if not isinstance(scenes, list):
            raise ValueError("Stored scenes must be a list")
        validated = [validate_scene(scene) for scene in scenes]
        self._scenes = {scene["id"]: scene for scene in validated}

    async def async_migrate(self, data: dict[str, Any], from_version: int) -> dict[str, Any]:
        """Migrate explicitly supported legacy envelopes."""
        if from_version == 0:
            return {"schema_version": STORAGE_VERSION, "scenes": data.get("scenes", [])}
        raise UnsupportedStorageVersion(f"No migration exists from schema version {from_version}")

    async def async_save_scene(self, value: dict[str, Any]) -> dict[str, Any]:
        """Validate before persisting and retain identity through name edits."""
        if self._read_only:
            raise UnsupportedStorageVersion("Future-version storage is read-only")
        scene = validate_scene(value)
        candidate = dict(self._scenes)
        candidate[scene["id"]] = scene
        await self._store.async_save(
            {"schema_version": STORAGE_VERSION, "scenes": list(candidate.values())}
        )
        self._scenes = candidate
        return scene

    async def async_delete_scene(self, scene_id: str) -> None:
        """Delete one saved user scene."""
        if self._read_only:
            raise UnsupportedStorageVersion("Future-version storage is read-only")
        candidate = dict(self._scenes)
        candidate.pop(scene_id, None)
        await self._store.async_save(
            {"schema_version": STORAGE_VERSION, "scenes": list(candidate.values())}
        )
        self._scenes = candidate
