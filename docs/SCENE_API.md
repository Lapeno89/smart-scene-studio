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
Mutating and read responses include `entity_sync.status`: `complete` means the native scene platform matches the saved scenes; `pending` means persistence succeeded but platform reconciliation did not. A pending
response is still a successful save, not a rollback. The next authenticated
list/get or mutation retries reconciliation from the latest Store snapshot
and reports its status.

## Commands

| Type | Additional fields | Result |
|---|---|---|
| `smart_scene_studio/scene/list` | none | `{ "scenes": [...] }` with built-ins and user scenes |
| `smart_scene_studio/scene/get` | `scene_id` | `{ "scene": {...} }` |
| `smart_scene_studio/scene/create` | `scene` | `{ "scene": {...} }`; the server assigns an immutable UUID |
| `smart_scene_studio/scene/update` | `scene_id`, `updates` | `{ "scene": {...} }`; only mutable fields are accepted |
| `smart_scene_studio/scene/duplicate` | `scene_id`, optional `name` | `{ "scene": {...} }`; creates a new user UUID |
| `smart_scene_studio/scene/delete` | `scene_id` | `{ "deleted": "<uuid>" }` |
| `smart_scene_studio/scene/export` | optional `scene_ids` | `{ "bundle": {"format", "version", "scenes": [...] } }` |
| `smart_scene_studio/scene/import` | `bundle`, `dry_run`, optional `target_mappings` | `{ "report": {...} }`; administrator-only |

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
The Store mutation and its platform reconciliation are serialized so concurrent
API requests cannot apply stale snapshots. Failed reconciliation leaves the
saved definition intact, is reported as pending, and can be retried by a later
API request. When targets are removed and later restored, Home Assistant's
entity registry retains the scene UUID and its entity ID.

## JSON portability

Export is available to any authenticated user. Omitting `scene_ids` exports all
built-in and user scenes; providing IDs selects only those scenes. Bundles use
format `smart_scene_studio.scene_bundle`, version `1`, and contain only validated
scene fields plus `provenance`. Unknown fields and exports larger than 1 MiB are
rejected. Bundles contain no credentials or Hue account information.

Import is administrator-only and requires an explicit `dry_run` boolean. A dry
run validates the entire bundle and returns a plan without writing the Store or
syncing native entities. It also checks the current 500-scene and 1 MiB Store
limits and reports `capacity.can_commit` plus any capacity errors. The preview
is serialized with scene mutations; a later commit still rechecks the limits
atomically because storage may change after the preview response. Committing
recomputes the plan while holding the same lock used for Store writes and entity
synchronization, then stores new scenes as one batch. A failed Store write
publishes none of the batch. Identical repeated source UUID definitions are
treated as duplicates and imported once; conflicting definitions with the same
source UUID are rejected. Other duplicate content is skipped, original UUIDs are
preserved when free, and collisions receive a deterministic derived UUID.
Repeating an unchanged import is idempotent.

Imported light IDs are never matched by scene or light name. `target_mappings`
must explicitly map source `light.*` IDs to destination `light.*` IDs. Assignments
without a mapping remain as disabled targets and are listed in the report, so an
unknown source light cannot be activated implicitly. Mappings for lights absent
from the bundle and multiple targets mapped to the same light within one scene
are rejected. Built-in provenance is retained for inspection, but imported
scenes are user-owned. Philips Hue Bridge access remains outside this increment.
No Hue Bridge, network address, household entity ID, token, or production Home
Assistant data is embedded in the integration or test fixtures.
