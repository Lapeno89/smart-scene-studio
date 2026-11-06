# Scene management WebSocket API

Smart Scene Studio exposes Home Assistant WebSocket commands under
`smart_scene_studio/scene/`. Use the authenticated `/api/websocket` connection.
Every read requires an authenticated Home Assistant user. All mutations are
administrator-only in this increment.

Scene definitions and target entity IDs are shared across authenticated users
of the Home Assistant instance; this integration has one shared scene Store.
Mutations are administrator-only. Before activating a scene on behalf of a
user, the integration checks Home Assistant's `control` permission for every
selected `light.*` target and propagates the caller context to light services.

All requests include the usual WebSocket `id` and a `type`. Responses use Home
Assistant's standard `success`/`result` or `success`/`error` envelope. Scene
objects are returned with `provenance` set to `builtin` or `user`.

## Commands

| Type | Additional fields | Result |
|---|---|---|
| `smart_scene_studio/scene/list` | none | `{ "scenes": [...] }` with built-ins and user scenes |
| `smart_scene_studio/scene/get` | `scene_id` | `{ "scene": {...} }` |
| `smart_scene_studio/scene/create` | `scene` | `{ "scene": {...} }`; the server assigns an immutable UUID |
| `smart_scene_studio/scene/update` | `scene_id`, `updates` | `{ "scene": {...} }`; only mutable fields are accepted |
| `smart_scene_studio/scene/duplicate` | `scene_id`, optional `name` | `{ "scene": {...} }`; creates a new user UUID |
| `smart_scene_studio/scene/delete` | `scene_id` | `{ "deleted": "<uuid>" }` |

Create requires a non-empty `name` and a `palette` containing 2–8 `#RRGGBB`
colors. Optional fields are `category`, `favorite`, `targets`,
`brightness_pct`, and `transition`; the shared scene validator applies the same
limits as persisted scene definitions. IDs, timestamps, provenance, unknown
fields, malformed targets, and oversized command bodies are rejected. Updates
preserve the original UUID and creation timestamp. Built-ins cannot be edited
or deleted; duplicate one to create a user-owned copy.

Storage writes are serialized, validated before persistence, and limited to 500
scenes and 1 MiB. Home Assistant's versioned `Store` handles atomic replacement.
If storage comes from a newer schema, it remains read-only and is never replaced
with empty data.

Native `scene.*` entities are added, updated and removed from the active entity
platform after persisted CRUD changes without requiring an integration reload.
When targets are removed and later restored, Home Assistant's entity registry
retains the scene UUID and its entity ID. JSON import/export and Philips Hue API
access are deferred. No Hue Bridge, network address, household entity ID,
token, or production Home Assistant data is embedded in the integration or
test fixtures.
