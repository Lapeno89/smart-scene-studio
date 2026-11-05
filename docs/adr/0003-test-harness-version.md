# ADR-0003: Pin the test runtime independently from fixture extraction

Status: accepted for PR-001
Date: 2026-11-05

## Context

Home Assistant Core 2026.11.0 is the project runtime target. At implementation time, the latest `pytest-homeassistant-custom-component` release is 0.13.375, whose extracted fixture package declares Home Assistant 2026.10.4. The package is generated from Home Assistant's tests and is updated independently from Core releases.

## Decision

Pin Home Assistant Core to 2026.11.0 and the fixture package to 0.13.375. Use uv's dependency override to keep the actual imported Home Assistant runtime on the project's 2026.11.0 pin while using the test fixture package. Revisit the fixture package pin as soon as it publishes a build for 2026.11.0.

## Consequences

The CI test runtime remains pinned to the stated Core release. Until the fixture package is regenerated, there is a compatibility risk in fixture extraction between 2026.10.4 and 2026.11.0. The integration tests must be run before treating this implementation as verified.
