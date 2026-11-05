# First Codex task — PR-001

Implement the **first local vertical slice** of Smart Scene Studio. Follow `AGENTS.md` and the documents in `docs/`. Do not begin with a frontend redesign, image upload, animation engine, or Hue importer.

## Required work
- Inspect the current workspace and official Home Assistant 2026.11 public developer interfaces. Prefer publicly documented APIs over copied upstream internals.
- Create the integration under `custom_components/smart_scene_studio/` with correct `manifest.json`, `config_flow.py`, lifecycle setup/unload, translations and `hacs.json`.
- Create a versioned `homeassistant.helpers.storage.Store` abstraction for user scenes; perform validation before write. Include migration hooks and a safe behavior for newer unknown schema versions.
- Ship three original, static builtin presets. Keep builtin resources immutable and custom definitions separately stored. Scene IDs must remain stable across name edits and restarts.
- Make persisted custom static scenes available as `scene.*` entities with unique IDs. Define dynamic entity addition/reload behavior; use HA-supported entity lifecycle patterns.
- Build a capability-aware light service wrapper; map a preset palette to an ordered selection of `light.*` entities. Handle missing/offline lights as partial outcomes, not global crashes. Support brightness and optional transition in the HA-supported form. Avoid unsupported color/white modes and avoid color-temperature shortcuts that cause color flashes.
- Include service/API calls needed for automated tests; any user-facing management action needs schema validation and appropriate permissions. Keep the first iteration minimal.
- Write pytest tests with `pytest-homeassistant-custom-component` for config flow, storage persistence, scene activation, incompatible color modes, unavailable devices, and integration reload. Tests must be executable and must not contact a real HA instance.
- Set up Ruff, type checking where practical, and GitHub Actions for lint/tests and hassfest/Marketplace validation when applicable.
- Add an install/development README and release/rollback documentation appropriate to the actual implemented feature set.

## Explicit exclusions for PR-001
No photo extraction, user image storage, animated light effects, Hue API calls, production install, remote repository creation, pushing or PR creation.

## Definition of done
1. A test Home Assistant instance can load/unload the integration.
2. A static scene is visible as a native scene entity and activates multiple supported lights.
3. Unsupported light capabilities don't receive unsupported fields.
4. Saved custom scenes survive an HA restart/reload and retain entity unique IDs.
5. Proper failure reporting; no crash from an offline light.
6. Source and docs in English; user report in Italian.
7. Exact commands and output of tests are reported, including any environment constraints.

Start by writing a very short implementation plan, then implement and test PR-001 locally. Do not ask broad architectural questions already answered by the docs. If API differences arise, document the decision in an ADR.
