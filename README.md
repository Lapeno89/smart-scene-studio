# Smart Scene Studio

Smart Scene Studio is an original Home Assistant custom integration for saved static light scenes. It uses Home Assistant `light.*` entities and does not require a Hue Bridge or direct Zigbee2MQTT access.

## Built-in static scenes

- Eleven original built-in scenes for ambient, relax, focus, warm-evening, ocean, forest, sunset, and white-light use.
- Native `scene.*` entities for scenes with at least one enabled light target.
- Versioned Home Assistant `Store` persistence for user scenes.
- The `smart_scene_studio.apply_scene` action applies a palette to explicitly selected light entities.
- Capability checks choose a supported XY, RGB, HS, RGBW, RGBWW, or brightness mode at activation time. White templates send only explicit Kelvin to entities supporting color temperature; incompatible, missing, and unavailable lights are skipped.
- Brightness is included only for dimmable lights. Transition is included only when the entity advertises transition support.
- Saved target assignments can be disabled, set to turn off, or given an explicit RGB color without changing scene identity.

Saved scenes can be managed through the authenticated Home Assistant WebSocket API described in [the scene API contract](docs/SCENE_API.md). Reads require an authenticated Home Assistant session; mutations require an administrator. Built-ins are read-only and can be duplicated into editable user scenes. Native `scene.*` entities are synchronized immediately after CRUD writes, preserve their UUID when renamed or reassigned, and are exposed only while a scene has at least one enabled light target. Targetless built-in templates remain available through the `apply_scene` action with explicit light entity IDs. All presets and color palettes are original; they do not include Hue gallery art, images, or logos.

## Installation

Copy `custom_components/smart_scene_studio` into the Home Assistant configuration's `custom_components` directory, restart Home Assistant, then add **Smart Scene Studio** through **Settings → Devices & services → Add integration**. Marketplace distribution requires adding the repository through the supported community integration workflow.

After setup, the **Smart Scene Studio** sidebar panel is registered automatically. Its compiled JavaScript ships inside the integration package; an installed Home Assistant instance does not need Node.js, a CDN, or a manual `/config/www` copy.

For the manually packaged `v0.1.0-alpha.1` test candidate, follow the [Italian installation and test checklist](docs/PRE_RELEASE_INSTALLATION_it.md). The candidate is not published to GitHub Releases or the Home Assistant Marketplace.

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
uv run python -c 'import homeassistant, pytest; raise SystemExit(pytest.main(["-q"]))'
```

Home Assistant Core is pinned to 2026.11.0 in `pyproject.toml`. The test runner imports Home Assistant before pytest plugin discovery so Core can install its httpx compatibility aliases. Tests stub light service calls and never target a physical Home Assistant instance.

## Storage and rollback

User scenes live in Home Assistant's managed `.storage` area under the key `smart_scene_studio.scenes`; they are not stored in the integration folder or `/config/www`. Back up Home Assistant before updating. If a future schema migration has run, reinstalling an older version may not be able to read that data. Restore a full backup from before the update to roll back. PR-001 does not yet provide scene export/import.

See [release and rollback notes](docs/RELEASE.md) and [the test plan](docs/TEST_PLAN.md).
