# Agent instructions — Smart Scene Studio

You are implementing an open-source Home Assistant custom integration named **Smart Scene Studio** (`smart_scene_studio`).

## Scope and authority
- Use only this repository's requirements and verified upstream source. Do **not** use previous user conversations or memory.
- The user authorizes planning and local code changes for the project. **Do not create or fork remote repositories, push commits, open PRs, access production Home Assistant, install integrations, or change devices without explicit, separate approval.**
- Implement in small, testable increments. Do not claim working Home Assistant integration without an integration-level test run.
- Primary target: Home Assistant 2026.11.0 and Python >=3.14.2. Check actual project pins and Home Assistant APIs before coding; do not silently import private or deprecated APIs.
- Communication with the user: Italian. Code, comments, tests, commit text, filenames, and documentation: English.
- Minimize dependencies, avoid blocking the event loop, and give proper cancellation/unload behavior.
- Original modules only in the first implementation. If upstream code is copied/adapted, add provenance and required LICENSE/NOTICE files, and mark modified files.

## First deliverable (PR-001)
Read `docs/TECHNICAL_SPEC.md`, `docs/adr/0001-architecture.md`, `docs/ROADMAP.md`, `docs/TEST_PLAN.md`, and `CODEX_START_PROMPT.md` before writing code.
Implement only the base service layer and a testable static-scene vertical slice:
1. HACS/Marketplace-compatible custom integration skeleton and UI config flow.
2. Versioned `Store`-backed saved scene definitions (outside integration directory), guarded validation and stable IDs; built-in presets shipped as read-only resources.
3. Native `scene.*` entities (stable unique IDs) and static scene application via Home Assistant `light.turn_on`, skipping missing/unavailable entities and unsupported modes.
4. Initially three original preset palettes (no borrowed Hue images). No image uploads or animations in PR-001.
5. Tests demonstrating reload and persistence, capable light handling, no unsupported payloads, and clean unload.
6. Minimal docs, automated lint/test configuration; do not overbuild frontend or backend abstractions.

## Engineering invariants
- Never require Philips Hue Bridge or Zigbee2MQTT direct MQTT integration for basic operation.
- Never mutate physical devices during tests: stub Home Assistant service calls.
- Do not store state in `custom_components/smart_scene_studio/userdata` or under public `/config/www`.
- Never infer lamp capability from product branding; inspect `supported_color_modes`, ranges and features.
- Avoid green/purple intermediate flashes when switching to white: send proper `color_temp_kelvin` only when supported, avoid mixed color+white payloads; document hardware-dependent behavior.
- Minimize writes and don't treat unsupported `transition` as guaranteed. If the underlying light doesn't support it, omit or reject it safely.
- No uncontrolled per-light loops or high-rate Zigbee commands.
- Preserve identity of scenes independent of their names.
- CI must run against pinned, documented Home Assistant requirements; no mock-only claims about hardware reliability.

## Completion response format
Report in Italian: files changed, commands/tests actually executed and exact outcome, anything untested, known limitations, and next increment. Never claim tests passed without execution.
