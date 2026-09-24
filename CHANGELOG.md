# Changelog

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
