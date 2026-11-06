"""Native scene entities for saved scenes and immutable presets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_REPOSITORY, DATA_SCENE_ENTITIES
from .light_control import async_apply_scene
from .models import scene_object_id, validate_scene


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Load built-in and persisted custom scene entities."""
    repository = hass.data[entry.domain][entry.entry_id][DATA_REPOSITORY]
    path = Path(__file__).with_name("presets.json")
    preset_text = await hass.async_add_executor_job(path.read_text, "utf-8")
    presets = [validate_scene(item) for item in json.loads(preset_text)]
    scene_definitions = (*presets, *repository.scenes)
    entities = [
        SmartScene(scene)
        for scene in scene_definitions
        if any(target["enabled"] for target in scene["targets"])
    ]
    hass.data[entry.domain][DATA_SCENE_ENTITIES] = {entity.unique_id: entity for entity in entities}
    async_add_entities(entities)


class SmartScene(Scene):
    """A stateless native scene backed by an immutable scene UUID."""

    def __init__(self, definition: dict[str, Any]) -> None:
        self._definition = definition
        self._attr_name = definition["name"]
        self._attr_unique_id = definition["id"]
        self._attr_suggested_object_id = scene_object_id(definition)

    async def async_activate(self, **kwargs: Any) -> None:
        """Activate the scene's saved target assignments."""
        await async_apply_scene(self.hass, self._definition)
