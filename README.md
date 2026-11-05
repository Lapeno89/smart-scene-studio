# Smart Scene Studio

Smart Scene Studio is an original Home Assistant custom integration for saved static light scenes. It uses Home Assistant `light.*` entities and does not require a Hue Bridge or direct Zigbee2MQTT access.

## PR-001 features

- Three built-in palettes: Amber Evening, Ocean Calm, and Rose Dawn.
- Native `scene.*` entities for built-in and saved scenes.
- Versioned Home Assistant `Store` persistence for user scenes.
- The `smart_scene_studio.apply_scene` action applies a palette to explicitly selected light entities.
- Capability checks choose a supported XY or RGB mode. White color temperature is only sent when explicitly selected with a valid Kelvin value and supported range. Unsupported, missing, and unavailable lights are skipped.
- Brightness is included only for dimmable lights. Transition is included only when the entity advertises transition support.

User scenes are currently written through the repository layer; a user-facing editor and CRUD action are not part of PR-001. Changes made through the internal repository are exposed as scene entities after reloading the integration. The built-in scene entities have no saved target assignments; apply a built-in palette to chosen lights with the `apply_scene` action.

## Installation

Copy `custom_components/smart_scene_studio` into the Home Assistant configuration's `custom_components` directory, restart Home Assistant, then add **Smart Scene Studio** through **Settings → Devices & services → Add integration**. For Marketplace distribution, publish the repository and add it to the Marketplace using its supported community integration workflow. No remote repository or Marketplace listing is created by this source package.

## Apply a preset

Use the `smart_scene_studio.apply_scene` action with a preset UUID and one or more light entity IDs. Example:

```yaml
action: smart_scene_studio.apply_scene
data:
  scene_id: b88ea8a1-0db4-4df5-9e91-4d93a3d30001
  entity_id:
    - light.living_room
    - light.reading_lamp
```

Transitions are best-effort and sent only when supported by the light entity. Device firmware and transport behavior require hardware testing; this project makes no hardware reliability claim based on mocked tests.

## Development

Requires Python 3.14.2 or newer and `uv`.

```sh
uv sync --group test
uv run ruff check .
uv run pytest -q
```

Home Assistant Core is pinned to 2026.11.0 in `pyproject.toml`. Tests stub `light.turn_on` and never target a physical Home Assistant instance.

## Storage and rollback

User scenes live in Home Assistant's managed `.storage` area under the key `smart_scene_studio.scenes`; they are not stored in the integration folder or `/config/www`. Back up Home Assistant before updating. If a future schema migration has run, reinstalling an older version may not be able to read that data. Restore a full backup from before the update to roll back. PR-001 does not yet provide scene export/import.

See [release and rollback notes](docs/RELEASE.md) and [the test plan](docs/TEST_PLAN.md).
