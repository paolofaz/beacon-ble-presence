"""Binary sensor platform for Beacon BLE Presence."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_MAJOR, CONF_MINOR, CONF_NAME, CONF_UUID, DOMAIN
from .coordinator import BeaconPresenceCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the presence binary sensor."""
    coordinator: BeaconPresenceCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BeaconPresenceBinarySensor(entry, coordinator)])


class BeaconPresenceBinarySensor(BinarySensorEntity):
    """Presence state for one configured iBeacon."""

    _attr_device_class = BinarySensorDeviceClass.PRESENCE
    _attr_has_entity_name = True
    _attr_translation_key = "presence"

    def __init__(self, entry: ConfigEntry, coordinator: BeaconPresenceCoordinator) -> None:
        """Initialize the sensor."""
        self._entry = entry
        self._coordinator = coordinator

        uuid = entry.data[CONF_UUID]
        major = entry.data[CONF_MAJOR]
        minor = entry.data[CONF_MINOR]
        name = entry.data[CONF_NAME]

        self._attr_unique_id = f"{uuid}_{major}_{minor}_presence"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{uuid}_{major}_{minor}")},
            "name": name,
            "model": "iBeacon",
        }

    @property
    def available(self) -> bool:
        """Remain unavailable until startup has produced a determinate state."""
        return self._coordinator.present is not None

    @property
    def is_on(self) -> bool | None:
        """Return whether the beacon is present."""
        return self._coordinator.present

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose compact diagnostics useful for debugging."""
        return {
            "last_seen": self._coordinator.last_seen.isoformat()
            if self._coordinator.last_seen
            else None,
            "last_scanner": self._coordinator.last_source,
            "uuid": self._coordinator.uuid,
            "major": self._coordinator.major,
            "minor": self._coordinator.minor,
            "presence_timeout": self._coordinator.timeout,
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator changes."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._coordinator.async_add_listener(self._async_coordinator_updated)
        )

    @callback
    def _async_coordinator_updated(self) -> None:
        """Write updated coordinator state."""
        self.async_write_ha_state()
