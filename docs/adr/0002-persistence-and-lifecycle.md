# ADR-0002: HA Store and stateless native scenes
Status: proposed
Date: 2026-11-05

## Decision
Use `homeassistant.helpers.storage.Store` for versioned user data with migration support and stable UUID scene IDs. Ship built-in presets as read-only packaged JSON. Expose saved static scenes as `scene.*` using the documented Home Assistant Scene platform and async activation method. Keep runtime animation state separate from persistent scene definitions.

## Consequences
Scenes should persist despite unavailable target lights. Home Assistant scenes do not represent current lamp state. Entity registration and deletion must be coordinated with save/delete operations to avoid orphan entities. Unknown future schema versions must not be overwritten by an older integration version. Data rollback requires version compatibility or an explicit exported backup.
