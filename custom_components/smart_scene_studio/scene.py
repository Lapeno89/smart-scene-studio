"""Native scene entities for saved scenes and immutable presets."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterable
from typing import Any, TypeVar

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Context, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    EntityPlatform,
    async_get_current_platform,
)

from .const import (
    DATA_PRESETS,
    DATA_REPOSITORY,
    DATA_SCENE_ENTITIES,
    DATA_SCENE_MANAGER,
)
from .light_control import async_apply_scene
from .models import scene_object_id

_LOGGER = logging.getLogger(__name__)
_MutationResult = TypeVar("_MutationResult")
SceneDefinitions = Callable[[], Iterable[dict[str, Any]]]
SceneMutation = Callable[[], Awaitable[_MutationResult]]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, _async_add_entities: AddEntitiesCallback
) -> None:
    """Load built-in and persisted custom scene entities."""
    entry_data = hass.data[entry.domain][entry.entry_id]
    repository = entry_data[DATA_REPOSITORY]
    presets = hass.data[entry.domain][DATA_PRESETS]
    manager = SceneEntityManager(async_get_current_platform())
    entry_data[DATA_SCENE_MANAGER] = manager
    hass.data[entry.domain][DATA_SCENE_ENTITIES] = manager.entities
    await manager.async_sync((*presets, *repository.scenes))


class SceneEntityManager:
    """Keep native scene entities aligned with persisted scene definitions."""

    def __init__(self, platform: EntityPlatform) -> None:
        self._platform = platform
        self.entities: dict[str, SmartScene] = {}
        self._lock = asyncio.Lock()
        self._sync_pending = False

    @property
    def sync_pending(self) -> bool:
        """Whether a persisted mutation still needs platform reconciliation."""
        return self._sync_pending

    async def async_sync(self, definitions: Iterable[dict[str, Any]]) -> None:
        """Add, update or remove scene entities without reloading the platform."""
        async with self._lock:
            await self._async_sync_locked(definitions)
            self._sync_pending = False

    async def async_mutate_and_sync(
        self,
        mutation: SceneMutation,
        definitions: SceneDefinitions,
    ) -> tuple[_MutationResult, bool]:
        """Serialize a Store mutation with reconciliation of its resulting snapshot."""
        async with self._lock:
            result = await mutation()
            try:
                # Read the repository only after the manager lock is held. Another
                # mutation cannot persist and then overtake this reconciliation.
                await self._async_sync_locked(definitions())
            except Exception:
                self._sync_pending = True
                _LOGGER.exception(
                    "Scene changes were persisted, but native entity synchronization failed"
                )
                return result, False
            except BaseException:
                # Cancellation must not leave a persisted write looking synchronized.
                self._sync_pending = True
                raise
            self._sync_pending = False
            return result, True

    async def async_reconcile_if_pending(self, definitions: SceneDefinitions) -> bool:
        """Retry a previously failed reconciliation using the latest saved snapshot."""
        if not self._sync_pending:
            return True

        async with self._lock:
            if not self._sync_pending:
                return True
            try:
                await self._async_sync_locked(definitions())
            except Exception:
                _LOGGER.exception("Could not retry pending native scene synchronization")
                return False
            self._sync_pending = False
            return True

    async def _async_sync_locked(self, definitions: Iterable[dict[str, Any]]) -> None:
        """Reconcile definitions while holding the manager lock."""
        all_definitions = {definition["id"]: definition for definition in definitions}
        desired = {
            scene_id: definition
            for scene_id, definition in all_definitions.items()
            if any(target["enabled"] for target in definition["targets"])
        }

        # Detect entities the platform failed to add or removed independently.
        for scene_id, entity in tuple(self.entities.items()):
            if self._platform.entities.get(entity.entity_id) is not entity:
                del self.entities[scene_id]
                if scene_id not in all_definitions:
                    er.async_get(self._platform.hass).async_remove(entity.entity_id)

        for scene_id in tuple(self.entities.keys() - desired.keys()):
            entity = self.entities[scene_id]
            entity_id = entity.entity_id
            await entity.async_remove(force_remove=True)
            if self._platform.entities.get(entity_id) is entity:
                raise RuntimeError(f"Home Assistant did not remove {entity_id}")
            if scene_id not in all_definitions:
                er.async_get(self._platform.hass).async_remove(entity_id)
            del self.entities[scene_id]

        new_entities: list[SmartScene] = []
        for scene_id, definition in desired.items():
            if entity := self.entities.get(scene_id):
                entity.async_update_definition(definition)
            else:
                new_entities.append(SmartScene(definition))

        if not new_entities:
            return

        await self._platform.async_add_entities(new_entities)
        failed_entity_ids = []
        for entity in new_entities:
            if self._platform.entities.get(entity.entity_id) is entity:
                self.entities[entity.unique_id] = entity
            else:
                failed_entity_ids.append(entity.entity_id)
        if failed_entity_ids:
            raise RuntimeError(
                "Home Assistant did not register scene entities: " + ", ".join(failed_entity_ids)
            )


class SmartScene(Scene):
    """A stateless native scene backed by an immutable scene UUID."""

    def __init__(self, definition: dict[str, Any]) -> None:
        self._definition = definition
        self._activation_context: Context | None = None
        self._attr_name = definition["name"]
        self._attr_unique_id = definition["id"]
        self._attr_suggested_object_id = scene_object_id(definition)

    @callback
    def async_set_context(self, context: Context) -> None:
        """Retain the caller context so light permission checks are preserved."""
        self._activation_context = context
        super().async_set_context(context)

    @callback
    def async_update_definition(self, definition: dict[str, Any]) -> None:
        """Update scene attributes in place while retaining the immutable ID."""
        self._definition = definition
        self._attr_name = definition["name"]
        self._attr_suggested_object_id = scene_object_id(definition)
        self.async_write_ha_state()

    async def async_activate(self, **kwargs: Any) -> None:
        """Activate the scene's saved target assignments."""
        await async_apply_scene(self.hass, self._definition, context=self._activation_context)
