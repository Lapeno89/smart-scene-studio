"""Native scene entities for saved scenes and immutable presets."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any

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

    async def async_sync(self, definitions: Iterable[dict[str, Any]]) -> None:
        """Add, update or remove scene entities without reloading the platform."""
        all_definitions = {definition["id"]: definition for definition in definitions}
        desired = {
            scene_id: definition
            for scene_id, definition in all_definitions.items()
            if any(target["enabled"] for target in definition["targets"])
        }
        async with self._lock:
            for scene_id in tuple(self.entities.keys() - desired.keys()):
                entity = self.entities[scene_id]
                await entity.async_remove(force_remove=True)
                if scene_id not in all_definitions:
                    er.async_get(self._platform.hass).async_remove(entity.entity_id)
                del self.entities[scene_id]

            new_entities = []
            for scene_id, definition in desired.items():
                if entity := self.entities.get(scene_id):
                    entity.async_update_definition(definition)
                else:
                    new_entities.append(SmartScene(definition))

            if new_entities:
                await self._platform.async_add_entities(new_entities)
                self.entities.update((entity.unique_id, entity) for entity in new_entities)


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
