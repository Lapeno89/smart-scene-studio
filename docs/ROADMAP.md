# Incremental roadmap

| Increment | Outcome | Evidence |
|---|---|---|
| PR-001 | Installable static backend, Store, 3 presets, native scene entities | HA test load/unload/restart, activation payload tests |
| PR-002 | Authenticated CRUD API and scene import/export | WebSocket or REST permission tests, schema validation |
| PR-003 | Gallery UI: preview/search/category/favorites, mobile + desktop | Frontend tests + manual HA dark/light theme checks |
| PR-004 | Secure image upload, palette extraction, 2-8 editable colors, thumbnail | Image security tests and photo corpus quality checks |
| PR-005 | Detailed per-lamp editor, balanced/random/sequence distribution | Mixed-mode capability tests |
| PR-006 | Dynamic scene scheduler with concurrency/budgets | Cancellation, offline, overlapping and load tests |
| PR-007 | Hue API V2 importer + stable device mapping | JSON fixtures, non-destructive dry run, incompatibility report |
| PR-008 | Performance, documentation, integration release | Real Zigbee2MQTT hardware matrix and upgrade/rollback tests |

No PR beyond PR-001 is authorized merely by inclusion in this roadmap. Changes to remote repositories or live HA require separate explicit permission.
