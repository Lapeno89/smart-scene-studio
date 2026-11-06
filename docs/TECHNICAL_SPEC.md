# Smart Scene Studio — Technical specification v0.1
Date: 2026-11-05
Status: proposed specification; no implementation or runtime verification is implied.

## Product intent
An original Home Assistant-integrated scene gallery and editor, primarily for Zigbee lights exposed as `light.*` by Zigbee2MQTT but vendor-independent. No mandatory Hue Bridge, cloud service, or direct MQTT access.

## Target platform
- Home Assistant Core 2026.11.0 as the first target. Python >=3.14.2 for matching local test environments.
- Deployment: custom integration via Home Assistant Marketplace (formerly HACS); one integration folder beneath `custom_components/` and all runtime assets inside it.
- Frontend phase: TypeScript + Lit-based Home Assistant custom panel, supplied as a built static asset. Avoid registering undocumented APIs without validation.

## Domain contracts
- `SceneDefinition` v1: UUID id; name; kind (`static` for first increment); category; favorite; optional thumbnail identifier; ordered palette with 2–8 RGB hex colors; ordered target assignments; global brightness and transition; created/updated metadata.
- `TargetAssignment`: Home Assistant entity identity and optional device identity; enable/on/off; color mode (`xy`, `rgb`, `color_temp_kelvin`, `brightness`, or none); chosen palette index or explicit color; optional brightness and transition; capability snapshot is advisory, never authoritative.
- `SceneRepository`: persist only user scenes, categories/collections and metadata in a versioned HA `Store`. Builtin presets are shipped as read-only resources. Atomic write semantics, schema checks, safe migration and export/import are required by later phases.
- `PaletteExtractor`: local bytes to normalized image to 2–8 perceptually useful colors. First implementation can use ColorThief with HA executor. Image upload, EXIF rotation, size/pixel limits and thumbnail handling are future work, not in PR-001.
- `LightAdapter`: use HA `light.turn_on` / `light.turn_off`. Determine effective color from supported modes at call time, not from static assumptions. Skip unavailable/unknown lights; report partial failures and do not silently turn a scene into incompatible RGB/CT instructions.
- `ScenePlatform`: static scenes represented by HA-native `scene.*`. `async_activate` calls the same service logic; changing a display name must not alter scene identity. HA scene entities are stateless, not a display of whether lights still match the scene.
- `AnimationScheduler` (later): centralized cancellation and lease/ownership for target lamps, bounded global and per-device command budgets, stop without sending queued stale commands; optional previous-state restore.
- `HueImporter` (later): read-only bridge extraction and reversible mapping, with an incompatibility report. Never delete source scenes or reset original devices.

## Requirements by phase
### PR-001: static backend slice
- Config flow, stable entity creation, static scene apply, Store and unit/integration tests.
- Three original presets, usable without a custom panel in a test HA setup.
- No direct Zigbee2MQTT calls. Ignore unsupported individual targets gracefully.

### MVP: gallery + images
- Galleria with category filters, search, favorites, preview and quick apply.
- Authenticated local photo uploads; JPG/PNG initially; 2–8 extracted colors; manual palette editing.
- Map palette colors to selected lights with balanced/sequential/shuffle distribution.
- Save scene name, thumbnail and immutable scene ID. Persistence after restart and updates.
- Authenticated API for list/create/update/delete/duplicate/apply. Authorization checks on every mutating endpoint.

### Extended editor
- Individual on/off, brightness, XY/RGB when available, Kelvin when available, individual transition where supported.
- Export/import versioned JSON, category collections, per-scene selection strategies and safe migrations.

### Dynamic effects
- Optional, bounded effects. Start, stop, pause, restore previous state, conflict resolution and metrics.
- No assumed gradient segment support; only expose it if surfaced by the relevant HA/device API.

### Hue migration
- Read the Hue v2 API where licensed and available; import compatible static parameters, preserve original Hue identifiers and maintain mapping to new HA light entity IDs. Smart Scenes and Entertainment effects need separate review.

## Performance and correctness
- No blocking filesystem reads, Pillow decode, or clustering in event loop.
- Avoid unconditional fan-out or unlimited task spawning. Duplicate targets should be deduplicated, preserving a deterministic assignment order.
- Transitions specified in seconds (Home Assistant API); never send both `xy_color` and `color_temp_kelvin` in one payload. For white-to-white, prefer white mode only. Hardware transitions still need device testing.
- Missing/offline entity should not cause persistent definition deletion.
- Don't automatically resume potentially hazardous/high-load dynamic effects after restart.
- Tests must include initial HA load/unload/reload and data schema upgrades with fixture migrations.

## Privacy and security
- Authentication/authorization for WebSocket commands and upload APIs. Validate entity permissions where appropriate, or use admin-only mutations initially.
- Reject path traversal, deceptive file extension, decompression bombs, oversized content, unsafe image formats; normalize images via safe decoder off event loop.
- Store thumbnails outside publicly exposed `/config/www`, behind authenticated routes. Original photo storage optional, off by default.
- Never embed HA tokens, Hue keys or other secrets in source, release assets, logs or test fixtures.

## Release engineering
- One open-source repo, license Apache-2.0 for original code; retain upstream license text and copyright notices for any reused material.
- Tests: pytest, Ruff, HA integration fixtures, frontend lint/unit tests when UI exists, hassfest, Marketplace/HACS validation.
- GitHub release tags and upgrade/rollback notes; do not assume downgrades work after storage migrations.

## Sources verified on 2026-11-05
- Scene Presets https://github.com/Hypfer/hass-scene_presets — `manifest.json` 2.4.0, Apache-2.0, Aug 9 2026 release commit b53280c76f6a94ea68f313c53865c3922d40b2d7.
- Chameleon https://github.com/MKSG-MugunthKumar/ha-chameleon — `manifest.json` 3.1.0, MIT; last inspected commit Oct 20 2026 4de4e055e980c2a57e084583b8a5d5baff79b874.
- https://contributors.home-assistant.io/core/entities/scene/
- https://contributors.home-assistant.io/marketplace/guides/integrations/
- https://contributors.home-assistant.io/frontend/custom-ui/panel/
- https://contributors.home-assistant.io/core/development/environment/
