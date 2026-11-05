# Test and acceptance plan

## PR-001 integration tests
- Setup/teardown: integration config flow, loaded `scene.*` entities, integration unload leaves no services/task leaks.
- Storage: fresh file, valid saved scene, reload preserving UUID and `unique_id`; malformed data and unsupported newer storage version cannot be silently destroyed; migration fixture exercise.
- Scene activation: two RGB/XY-compatible lights receive appropriate service calls with correct brightness and transition representation.
- Capability fallback: white-only light gets `color_temp_kelvin` only if explicitly supported; brightness-only gets no color attribute; unavailable and missing lights get no commands.
- Error semantics: one light raises, another succeeds; action reports partial failure without corrupting persistent scenes.
- Runtime: no direct Zigbee2MQTT publish and no actual HA device control in tests.
- Stability: rename scene without changing `unique_id`, delete scene removes registry entity, builtin presets immutable.

## Later photo/gallery tests
- Images: JPEG/PNG, rotated EXIF, all-white, all-black, low-light, dominant colorful object, transparent PNG, oversized pixel count, corrupt/truncated data and path traversal attempts.
- Palette count: 2–8, deterministic for fixed seed/settings, duplicates are handled, editable output survives reload.
- UI: light/dark themes, responsive touch targets, no unintended API traffic in preview, authenticated upload and CRUD.
- Zigbee: verify command budget, rate limiter, offline recovery, cancellation, mode switch white/colored light and physical-device color transition. Simulator success is not hardware proof.
- Hue: dry run, read-only source, mapping ambiguous IDs and reporting missing gradients/dynamic features.

## Required evidence per increment
Record exact test command, environment versions, exit status, number of tests passing/failing and known untested hardware assumptions. Do not claim compatibility with untested devices.
