# Test and acceptance plan

## PR-001 integration tests
- Setup/teardown: integration config flow, targetless built-ins and saved scenes are not exposed as native entities, assigned scenes load as `scene.*`, and unload leaves no services/task leaks.
- Storage: fresh file, valid saved scene, reload preserving UUID and `unique_id`; malformed data and unsupported newer storage version cannot be silently destroyed; migration fixture exercise.
- Scene activation: `scene.turn_on` on a registered assigned scene invokes `light.turn_on` for its configured light; preset service activation requires explicit targets. Compatible RGB/XY/HS/RGBW/RGBWW lights receive supported payloads with correct brightness and transition representation.
- Capability fallback: white-only lights get `color_temp_kelvin` only if explicitly selected and supported; brightness-only lights get no color attribute; unavailable and missing lights get no commands.
- Target intent: disabled assignments are skipped, off assignments call `light.turn_off`, and explicit RGB colors override palette selection.
- Error semantics: one light raises, another succeeds; action reports partial failure without corrupting persistent scenes.
- Runtime: no direct Zigbee2MQTT publish and no actual HA device control in tests.
- Stability: rename scene without changing `unique_id`, delete scene removes registry entity, builtin presets immutable.

## PR-002 scene API and entity synchronization
- WebSocket access: anonymous handshakes cannot enter command phase; authenticated users can list/get; non-admin mutation attempts fail; administrator CRUD succeeds.
- Live native entity sync: targetful create registers `scene.*`; rename keeps the entity instance and `unique_id`; removing all enabled targets unloads the entity; restoring targets reuses its entity ID; delete removes it without integration reload.
- Persistence/recovery: API-created scenes survive integration reload; concurrent update/delete leave Store and memory consistent; controlled concurrent API mutations leave the final native entity names and targets identical to the final persisted snapshot; Store failures do not return success or publish transient entities; platform reconciliation failures preserve saved scenes, report entity_sync pending, and retry on a later API request; count and serialized-size limits reject before writing.
- Compatibility: PR-001 schema-v1 scenes load with the same UUID; unsupported future storage versions remain read-only and are not overwritten.
- Authorization: scene data visibility is shared for authenticated users, writes require an admin, and the actual scene.turn_on service path uses each invocation's real limited-user policy for POLICY_CONTROL, blocks denied lights before any light call, forwards allowed calls with that invocation's context, and does not reuse a previous caller context.

## JSON portability
- Export: authenticated users can export all scenes or selected IDs; builtin/user provenance is retained and unknown/secret fields never appear.
- Import validation: enforce version, schema, JSON compatibility, 1 MiB/scene limits, strict fields and explicit light ID mappings; disable unmapped targets and report them.
- Import planning: dry-run does not mutate Store or native entities; preserve free UUIDs, deterministically derive colliding identities, skip duplicate content and remain idempotent.
- Import persistence: admin-only commit recomputes under the scene manager lock, writes the full batch atomically, synchronizes native entities, and preserves Store state when batch persistence fails.

## Later photo/gallery tests
- Images: JPEG/PNG, rotated EXIF, all-white, all-black, low-light, dominant colorful object, transparent PNG, oversized pixel count, corrupt/truncated data and path traversal attempts.
- Palette count: 2–8, deterministic for fixed seed/settings, duplicates are handled, editable output survives reload.
- UI: light/dark themes, responsive touch targets, no unintended API traffic in preview, authenticated upload and CRUD.
- Zigbee: verify command budget, rate limiter, offline recovery, cancellation, mode switch white/colored light and physical-device color transition. Simulator success is not hardware proof.
- Hue: dry run, read-only source, mapping ambiguous IDs and reporting missing gradients/dynamic features.

## Required evidence per increment
Record exact test command, environment versions, exit status, number of tests passing/failing and known untested hardware assumptions. Do not claim compatibility with untested devices.

Run the integration suite with Home Assistant initialized before pytest discovers plugins:

```sh
uv run python -c 'import homeassistant, pytest; raise SystemExit(pytest.main(["-q"]))'
```
