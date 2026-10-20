# Changelog

## 1.2.0 — Removed diagnostic sensor to preserve recorder from spam

## 1.1.0 — Memory bounds, lighter diagnostics and regression tests

- Limit stored rotating BLE addresses to 128 recent candidates per configured beacon and expire stale addresses.
- Continue inspecting Home Assistant's Bluetooth cache every five seconds; publish redundant diagnostic updates at most once every 60 seconds.
- Publish presence transitions immediately without changing the configured timeout.
- Reject stale cached advertisements as proof of presence after startup or timeout.
- Add 11 automated regression tests and a dedicated GitHub Actions unit test workflow.
- Explain the separate purpose of this selected-beacon binary sensor alongside Home Assistant's official iBeacon Tracker.
- **Existing configuration entries, UUID/Major/Minor values, device identities and entity unique IDs are unchanged.** Update in place without deleting the integration.


All notable changes to **Beacon BLE Presence** are documented here.

## 1.0.0 - 2026-09-23

### Added

- First stable public release.
- Passive iBeacon presence tracking by UUID, Major and Minor.
- Uses Home Assistant's central Bluetooth stack and existing Bluetooth proxies.
- Configurable presence timeout, with a conservative 180-second default.
- Restart-safe startup behavior designed to avoid artificial presence transitions.
- Compact diagnostics through `last_seen` and `last_scanner` attributes.
- English and Italian translations.
- Local Home Assistant brand icon.
- HACS and hassfest validation workflows.
