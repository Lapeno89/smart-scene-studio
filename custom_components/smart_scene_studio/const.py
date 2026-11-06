"""Constants for Smart Scene Studio."""

from typing import Final

DOMAIN: Final = "smart_scene_studio"
PLATFORMS: Final = ["scene"]
STORAGE_VERSION: Final = 1
STORAGE_MINOR_VERSION: Final = 0
STORAGE_KEY: Final = f"{DOMAIN}.scenes"
DATA_REPOSITORY: Final = "repository"
DATA_SCENE_ENTITIES: Final = "scene_entities"
DATA_PRESETS: Final = "presets"
DATA_SCENE_MANAGER: Final = "scene_manager"
SERVICE_APPLY_SCENE: Final = "apply_scene"
PRESETS_FILE: Final = "presets.json"
