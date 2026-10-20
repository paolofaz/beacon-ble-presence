# Beacon BLE Presence

**Beacon BLE Presence** is a custom integration for Home Assistant that provides deterministic presence binary sensors for selected iBeacons identified by **UUID + Major + Minor**.

It uses Home Assistant's existing Bluetooth stack and Bluetooth proxies. It does **not** start its own BLE scanner and does **not** depend on the official iBeacon Tracker integration.

## Why use this instead of the built-in iBeacon Tracker?

Home Assistant already provides the official **iBeacon Tracker** integration, which automatically discovers iBeacons and creates device trackers and additional diagnostic sensors. That is a good choice for general iBeacon tracking.

**Beacon BLE Presence** is a narrower alternative for selected beacons:

- **Explicit identity:** Add exactly the UUID + Major + Minor that you want to monitor; other broadcasts create no entities here.
- **One binary presence sensor per beacon:** A simple `on` / `off` entity suitable for automations, rather than automatic tracker discovery.
- **Configurable presence timeout per device:** Set 10–3600 seconds, with a default of 180 seconds, directly in the UI.
- **Conservative restart handling:** Cached packets from before Home Assistant restarts cannot create fake arrivals. An initial absence is established after the configured timeout.
- **Minimal diagnostics:** Last-seen time and scanner details are included as attributes; there is no RSSI localization or distance estimation.

This integration does not replace the official iBeacon Tracker for broad discovery. Both use the same public Home Assistant Bluetooth system.

## Features

- One presence binary sensor per configured iBeacon.
- Identifies beacons by UUID, Major and Minor.
- Works with Bluetooth advertisements already received by Home Assistant, including compatible ESPHome Bluetooth proxies.
- Configurable presence timeout; default: **180 seconds**.
- Restart-safe startup behavior to avoid artificial `off -> on` or `on -> off` transitions.
- Compact diagnostics: `last_seen`, `last_scanner`, UUID, Major, Minor and timeout.
- No RSSI positioning, strongest-scanner logic or room localization.
- English and Italian UI translations.

The integration has been tested with **DX-CP27** devices configured in iBeacon mode, but it is designed around the standard Apple iBeacon manufacturer payload rather than that specific model.

## Installation with HACS

After this repository has been published on GitHub:

1. Open HACS in Home Assistant.
2. Add `https://github.com/paolofaz/beacon-ble-presence` as a custom repository of type **Integration** if it is not yet in the HACS default store.
3. Install **Beacon BLE Presence**.
4. Restart Home Assistant.
5. Go to **Settings -> Devices & services -> Add integration** and search for **Beacon BLE Presence**.

## Manual installation

Copy:

```text
custom_components/beacon_ble_presence/
```

to:

```text
/config/custom_components/beacon_ble_presence/
```

Restart Home Assistant and add **Beacon BLE Presence** from **Settings -> Devices & services -> Add integration**.

## Configuration

Create one config entry for each iBeacon. The required fields are:

- **Name**: friendly device name.
- **UUID**: iBeacon proximity UUID.
- **Major**: integer from 0 to 65535.
- **Minor**: integer from 0 to 65535.
- **Presence timeout**: seconds without a fresh advertisement before presence becomes `off`.

Example:

```text
Name: Backpack
UUID: 12345678-1234-1234-1234-123456789abc
Major: 1
Minor: 1
Presence timeout: 180
```

The timeout can later be changed from the integration's **Configure** / **Options** dialog without deleting the beacon.

## How presence is determined

Home Assistant Bluetooth callbacks intentionally suppress duplicate advertisements. For reliable presence, this integration therefore uses a two-part approach:

1. a passive Home Assistant Bluetooth callback identifies addresses advertising the configured iBeacon identity;
2. a short periodic check reads Home Assistant's central Bluetooth cache to obtain the real timestamp of the newest advertisement for those addresses.

This keeps `last_seen` current without starting a separate scanner.

To avoid unbounded memory growth when MAC addresses rotate, the integration retains a maximum of **128 recent BLE addresses per beacon**. Addresses expire after an hour or twice the configured timeout, whichever is longer.

The cache and presence timeout are still checked every **5 seconds**. During continuous presence, diagnostic state updates are published at most once every **60 seconds**, reducing unnecessary Recorder writes. **Present/absent transitions are always published immediately**, without waiting for that diagnostic interval.

The binary sensor is:

- **on** when a live matching advertisement has been observed recently;
- **off** when no fresh advertisement has been observed for the configured timeout;
- temporarily **unavailable** after integration startup until a determinate state can be established.

## Restart behavior

Startup behavior is intentionally conservative.

A cached advertisement from before the integration started may be used to discover the beacon address, but it is **not** allowed to restore the sensor to `on`. The sensor becomes `on` only after an advertisement observed after startup.

If no live matching advertisement arrives, the sensor becomes `off` after the configured timeout. This prevents a Home Assistant restart from being interpreted by automations as a real beacon arrival or departure.

Automations that represent physical movement should therefore trigger on explicit transitions such as:

```yaml
from: "off"
to: "on"
```

or:

```yaml
from: "on"
to: "off"
```

rather than `unavailable -> on` or `unavailable -> off`.

## Diagnostics

The presence binary sensor exposes these attributes:

- `last_seen`: timestamp of the newest matching BLE advertisement known to Home Assistant;
- `last_scanner`: source identifier reported by Home Assistant Bluetooth;
- `uuid`;
- `major`;
- `minor`;
- `presence_timeout`.

`last_scanner` is diagnostic only. It should **not** be treated as a reliable physical location of the beacon.

## Design scope

Beacon BLE Presence deliberately focuses on a small, deterministic presence problem. It does not implement:

- RSSI-based checkpoints;
- strongest-scanner selection;
- room localization;
- RSSI peak/history analysis;
- its own Bluetooth scanning.

## Security and privacy

An iBeacon broadcasts its UUID, Major and Minor without cryptographic authentication. Other devices can imitate that identity. Do not use a beacon's presence as the only condition for unlocking doors or disarming security systems.

## Upgrading an existing installation

**Update the integration in place.** UUID, Major, Minor, entity `unique_id` and existing config entries remain unchanged; you do not need to re-enter your beacon identifiers. Back up Home Assistant before upgrading, and do not remove/recreate the configuration entries to update.

## Quality checks

Automated HACS and Hassfest validation runs on GitHub. An additional `tests/` suite covers payload parsing, rotating MAC expiration and bounds, passive callbacks, restart safety, timeout transitions and diagnostic throttling:

```sh
python -m unittest discover -s tests -v
```

## Compatibility

- Home Assistant 2026.3 or newer for the supported local custom-integration brand assets.
- Home Assistant Bluetooth must be available through a local adapter and/or supported Bluetooth proxies.
# 🍺 Support the Project

If you found this project useful and want to support my work, you can offer me a beer:

[![Buy Me a Beer](https://img.shields.io/badge/Buy%20Me%20a%20Beer-0070ba?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/PaoloFazari)


## Contributions
Contributions are welcome
