"""Constants for Beacon BLE Presence."""

DOMAIN = "beacon_ble_presence"
PLATFORMS = ["binary_sensor"]

CONF_NAME = "name"
CONF_UUID = "uuid"
CONF_MAJOR = "major"
CONF_MINOR = "minor"
CONF_TIMEOUT = "presence_timeout"

# Conservative default validated with 1.5 s iBeacon advertising in a multi-proxy home.
DEFAULT_TIMEOUT = 180
MIN_TIMEOUT = 10
MAX_TIMEOUT = 3600

# Apple iBeacon manufacturer payload: company 0x004C, prefix 0x02 0x15.
APPLE_MFR_ID = 0x004C
IBEACON_PREFIX = bytes((0x02, 0x15))

# Duplicate BLE advertisements are intentionally suppressed by HA callbacks.
# Periodically inspect HA's central Bluetooth cache to refresh the real last_seen.
REFRESH_INTERVAL_SECONDS = 5
