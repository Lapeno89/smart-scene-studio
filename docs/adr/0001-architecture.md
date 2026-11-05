# ADR-0001: Independent custom integration with reusable algorithms
Status: proposed, awaiting implementation validation
Date: 2026-11-05

## Context
Scene Presets already has a React-based visual gallery and HA light actions; Chameleon includes a local ColorThief-based photo palette extractor and light animation facilities. However, neither provides the complete desired persistent CRUD data model and editor. A full fork would import design and maintenance constraints; coordinating two independently installed integrations would introduce runtime coupling and overlapping effects management.

## Decision
Build one independent `smart_scene_studio` HA integration. Initially use only original code while taking algorithms and patterns as inspiration. Reuse specific upstream code in later patches only with provenance review and legally required notices. Prefer Home Assistant light entities as the control plane and make any Zigbee2MQTT-specific optimization an optional adapter.

## Tradeoffs
Additional initial work, but one schema, one lifecycle, one UI, one upgrade path and no dependency on separate custom integrations. A dedicated TypeScript/Lit panel is proposed once backend behavior and persistence are proven.

## Alternatives rejected for now
A) Scene Presets fork + Chameleon modules: short-term gallery advantage, difficult long-term data model changes.
B) Glue integration requiring both: fastest prototype, no ownership of dependencies and competing dynamic schedulers.

## Review triggers
If a verified upstream project gains a matching data model, persistent scene entities, user-photo upload/editor and stable API, revisit reuse choices.
