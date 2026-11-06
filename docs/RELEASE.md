# Release and rollback

## PR-001 local package

PR-001 is an initial implementation under review in the GitHub repository. It is not merged into the development branch or published to the Home Assistant Marketplace. Before distribution, run the repository CI, hassfest, Marketplace validation, and Home Assistant integration tests.

## Upgrade

Back up Home Assistant before installing a new integration version. The integration stores user scenes in Home Assistant-managed storage using schema version 1. Built-in presets are shipped read-only with the integration.

## Rollback

Remove the integration entry before removing its code. Restore the Home Assistant backup if a later release has migrated scene storage to a schema that an older release cannot read. Do not manually delete `.storage` files while Home Assistant is running. PR-001 has no export/import or downgrade migration guarantees.
