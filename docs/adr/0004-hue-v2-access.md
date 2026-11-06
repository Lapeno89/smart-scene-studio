# ADR-0004: Read-only Hue V2 access through Home Assistant's configured integration

Status: accepted for the Hue importer increment
Date: 2026-11-06

## Context

The Hue importer must read Bridge V2 scenes without making Smart Scene Studio a
second credential store or pairing client. Home Assistant 2026.11.0's Hue
integration already owns pairing, app-key storage, local API setup, and the
loaded V2 resource controllers. Its scene platform reads from `runtime_data.api`
and resolves scene groups through the scenes controller. The API's full-state
refresh is used by the configured integration during initialization.

## Decision

Require a loaded Home Assistant Philips Hue V2 config entry. On an explicit
administrator import request, refresh the existing API resource cache using its
read-only full-state fetch, then copy allow-listed scene/action/palette data into
the Smart Scene Studio Store. Listing and later remapping use cached/local data.
The importer does not expose host or app key, pair a bridge, use Hue cloud, or
recall/change/delete Hue scenes. Scene activation after import only calls the
existing Home Assistant `light.*` targets.

Hue resource IDs are never inferred to be Home Assistant IDs. Administrators
explicitly map resource UUIDs to entity registry choices; unmapped action data is
stored for later remapping. Source identity includes both bridge and scene UUID.
Static XY and Mirek settings are retained; dynamic, gradient, effect, and image
features are reported but not executed or copied.

## Consequences

- Smart Scene Studio still runs with no Hue config entry.
- No Hue credential is added to the Smart Scene Studio Store or its exports.
- The test suite uses synthetic JSON and a fake Hue runtime; it makes no network
  requests and does not initialize the Home Assistant Hue integration.
- The importer depends on the configured Hue integration's typed runtime API,
  which is an upstream implementation interface rather than a dedicated public
  cross-integration service. Keep the dependency isolated in the WebSocket
  adapter and recheck it whenever the pinned Home Assistant version changes.
- Static snapshots survive bridge removal. Re-import is keyed by bridge + Hue
  scene UUID and does not overwrite later local edits.

## Upstream implementation reviewed

- Home Assistant 2026.11.0 Hue scene platform:
  https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/hue/scene.py
- Home Assistant 2026.11.0 Hue bridge runtime:
  https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/hue/bridge.py
- Home Assistant 2026.11.0 Hue config flow and stored app-key fields:
  https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/hue/config_flow.py
