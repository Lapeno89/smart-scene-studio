# Release and rollback

## `v0.1.0-alpha.1` release candidate

The candidate is built from the composite UI feature branch after PR #11's frontend, Python, Ruff, Hassfest, and HACS checks pass. The Home Assistant integration manifest uses `0.1.0-alpha.1`; the proposed Git tag and archive name use the conventional leading `v`. The archive metadata records both versions and the exact source commit. No GitHub release or tag is published without the repository owner's approval.

Build the reproducible manual-install ZIP from a clean committed checkout with:

```sh
python scripts/build_release_zip.py
```

The command validates version alignment, required integration files and frontend bundle, candidate commit, and prohibited files. The ZIP contains `custom_components/smart_scene_studio/`, the root Apache-2.0 `LICENSE`, and `RELEASE_CANDIDATE.json`. It excludes development tools, tests, Python caches, credentials, and `node_modules`. The installed Home Assistant host needs no Python, Node.js, npm, CDN access, or `/config/www` copy for this integration.

The release candidate is a direct manual ZIP because this pre-release has not been published and is not on the repository's default branch. Do not instruct testers to install the default branch through Home Assistant Marketplace. Home Assistant's Marketplace release workflow requires a published release and the integration manifest version must match its tag. See the [Home Assistant release guide](https://contributors.home-assistant.io/marketplace/guides/releases/) and [2026.11 Marketplace announcement](https://www.home-assistant.io/blog/2026/11/04/release-202611).

## Before installing

Back up Home Assistant using **Settings → System → Backups** and download a copy somewhere outside the HA host. Record a copy of any previously installed integration folder. Custom integrations update by replacing the integration folder, and an already loaded integration requires a Home Assistant restart after replacement or removal.

## Upgrade and rollback

User scenes are stored in Home Assistant-managed `.storage` data, not in the integration directory. Do not remove that storage file manually. To remove the integration, first delete its entry in **Settings → Devices & services**, shut down Home Assistant before deleting `custom_components/smart_scene_studio`, then restart. The integration's storage key is not deleted by its unload callback, but this alpha makes no downgrade guarantee after any future storage migration.

To roll back, reinstall the previous integration folder while Home Assistant is stopped and restart. If the previous code cannot read the current stored scene schema, restore the complete backup made before installation. Never delete or edit `.storage` while Home Assistant is running.
