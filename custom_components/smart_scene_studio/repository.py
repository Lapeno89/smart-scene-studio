"""Versioned Home Assistant Store-backed scene repository."""

from __future__ import annotations

import asyncio
import json
from copy import deepcopy
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
        self._lock = asyncio.Lock()

    @property
    def scenes(self) -> tuple[dict[str, Any], ...]:
        """Return scenes in deterministic insertion order."""
        return tuple(deepcopy(scene) for scene in self._scenes.values())

    @property
    def read_only(self) -> bool:
        """Whether storage was created by a newer integration version."""
        return self._read_only

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
        if len({scene["id"] for scene in validated}) != len(validated):
            raise ValueError("Stored scenes must have unique IDs")
        self._scenes = {scene["id"]: scene for scene in validated}

    async def async_migrate(self, data: dict[str, Any], from_version: int) -> dict[str, Any]:
        """Migrate explicitly supported legacy envelopes."""
        if from_version == 0:
            return {"schema_version": STORAGE_VERSION, "scenes": data.get("scenes", [])}
        raise UnsupportedStorageVersion(f"No migration exists from schema version {from_version}")

    async def async_save_scene(self, value: dict[str, Any]) -> dict[str, Any]:
        """Validate before persisting and retain identity through name edits."""
        scene = validate_scene(value)
        async with self._lock:
            self._ensure_writable()
            candidate = dict(self._scenes)
            candidate[scene["id"]] = scene
            await self._async_save_candidate(candidate)
            self._scenes = candidate
            return deepcopy(scene)

    async def async_save_scenes(self, values: list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
        """Atomically add a batch of imported scenes without overwriting existing IDs."""
        scenes = [validate_scene(value) for value in values]
        scene_ids = [scene["id"] for scene in scenes]
        if len(set(scene_ids)) != len(scene_ids):
            raise ValueError("Imported scenes must have unique IDs")

        async with self._lock:
            self._ensure_writable()
            candidate = dict(self._scenes)
            for scene in scenes:
                if scene["id"] in candidate:
                    raise ValueError(f"Imported scene ID already exists: {scene['id']}")
                candidate[scene["id"]] = scene
            if scenes:
                await self._async_save_candidate(candidate)
                self._scenes = candidate
            return tuple(deepcopy(scene) for scene in scenes)

    async def async_check_batch_capacity(self, values: list[dict[str, Any]]) -> dict[str, Any]:
        """Predict whether an atomic batch can fit without writing to the Store."""
        scenes = [validate_scene(value) for value in values]
        scene_ids = [scene["id"] for scene in scenes]
        errors = []
        if len(set(scene_ids)) != len(scene_ids):
            errors.append("Imported scenes must have unique IDs")

        async with self._lock:
            candidate = dict(self._scenes)
            if self._read_only:
                errors.append("Future-version storage is read-only")
            for scene in scenes:
                if scene["id"] in candidate:
                    errors.append(f"Imported scene ID already exists: {scene['id']}")
                else:
                    candidate[scene["id"]] = scene
            errors.extend(self._candidate_capacity_errors(candidate))
            return {
                "can_commit": not errors,
                "current_scene_count": len(self._scenes),
                "proposed_scene_count": len(candidate),
                "max_scenes": 500,
                "errors": list(dict.fromkeys(errors)),
            }

    async def async_delete_scene(self, scene_id: str) -> None:
        """Delete one saved user scene."""
        async with self._lock:
            self._ensure_writable()
            if scene_id not in self._scenes:
                raise KeyError(scene_id)
            candidate = dict(self._scenes)
            del candidate[scene_id]
            await self._async_save_candidate(candidate)
            self._scenes = candidate

    async def async_update_scene(self, scene_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Atomically update mutable fields while preserving scene identity."""
        async with self._lock:
            self._ensure_writable()
            current = self._scenes.get(scene_id)
            if current is None:
                raise KeyError(scene_id)
            updated = validate_scene({**current, **updates, "id": scene_id})
            candidate = dict(self._scenes)
            candidate[scene_id] = updated
            await self._async_save_candidate(candidate)
            self._scenes = candidate
            return deepcopy(updated)

    def _ensure_writable(self) -> None:
        if self._read_only:
            raise UnsupportedStorageVersion("Future-version storage is read-only")

    async def _async_save_candidate(self, candidate: dict[str, dict[str, Any]]) -> None:
        """Persist a complete candidate before publishing it in memory."""
        errors = self._candidate_capacity_errors(candidate)
        if errors:
            raise ValueError(errors[0])
        data = {"schema_version": STORAGE_VERSION, "scenes": list(candidate.values())}
        await self._store.async_save(data)

    @staticmethod
    def _candidate_capacity_errors(candidate: dict[str, dict[str, Any]]) -> list[str]:
        """Apply the same count and serialized-size limits used by Store writes."""
        errors = []
        if len(candidate) > 500:
            errors.append("A maximum of 500 user scenes can be stored")
        data = {"schema_version": STORAGE_VERSION, "scenes": list(candidate.values())}
        if len(json.dumps(data, separators=(",", ":"))) > 1_048_576:
            errors.append("Scene storage exceeds the 1 MiB limit")
        return errors
