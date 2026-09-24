"""Presence coordinator for Beacon BLE Presence."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
import logging
import time

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.match import BluetoothCallbackMatcher
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    APPLE_MFR_ID,
    CONF_MAJOR,
    CONF_MINOR,
    CONF_TIMEOUT,
    CONF_UUID,
    DEFAULT_TIMEOUT,
    IBEACON_PREFIX,
    REFRESH_INTERVAL_SECONDS,
)
from .parser import parse_ibeacon

_LOGGER = logging.getLogger(__name__)


class BeaconPresenceCoordinator:
    """Track one configured iBeacon through Home Assistant Bluetooth."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry

        self.uuid: str = entry.data[CONF_UUID]
        self.major: int = entry.data[CONF_MAJOR]
        self.minor: int = entry.data[CONF_MINOR]
        self.timeout: int = entry.options.get(
            CONF_TIMEOUT, entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
        )

        self.present: bool | None = None
        self.last_seen: datetime | None = None
        self.last_source: str | None = None

        self._known_addresses: set[str] = set()
        self._listeners: set[Callable[[], None]] = set()
        self._started_monotonic = time.monotonic()
        self._last_service_monotonic: float | None = None

    async def async_start(self) -> None:
        """Start passive Bluetooth tracking and periodic cache checks."""
        self.entry.async_on_unload(
            bluetooth.async_register_callback(
                self.hass,
                self._async_bluetooth_event,
                BluetoothCallbackMatcher(
                    connectable=False,
                    manufacturer_id=APPLE_MFR_ID,
                    manufacturer_data_start=list(IBEACON_PREFIX),
                ),
                bluetooth.BluetoothScanningMode.PASSIVE,
                replay=bluetooth.BluetoothCallbackReplay.NEWEST_FIRST,
            )
        )

        self.entry.async_on_unload(
            async_track_time_interval(
                self.hass,
                self._async_periodic_refresh,
                timedelta(seconds=REFRESH_INTERVAL_SECONDS),
            )
        )

        # Callback replay is synchronous; this lets us inspect any addresses it found.
        self._async_refresh_from_bluetooth_cache()

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Subscribe an entity to coordinator updates."""
        self._listeners.add(listener)

        @callback
        def _remove_listener() -> None:
            self._listeners.discard(listener)

        return _remove_listener

    @callback
    def _async_notify_listeners(self) -> None:
        for listener in tuple(self._listeners):
            listener()

    @callback
    def _matches(self, service_info: bluetooth.BluetoothServiceInfoBleak) -> bool:
        parsed = parse_ibeacon(service_info)
        return bool(
            parsed
            and parsed.uuid == self.uuid
            and parsed.major == self.major
            and parsed.minor == self.minor
        )

    @callback
    def _async_bluetooth_event(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Handle a discovery/replay callback for matching iBeacon-shaped packets."""
        del change
        if not self._matches(service_info):
            return

        self._known_addresses.add(service_info.address)
        self._async_consider_service_info(service_info)

    @callback
    def _async_periodic_refresh(self, _now: datetime) -> None:
        """Refresh last_seen from HA's central Bluetooth cache."""
        self._async_refresh_from_bluetooth_cache()

    @callback
    def _async_refresh_from_bluetooth_cache(self) -> None:
        freshest: bluetooth.BluetoothServiceInfoBleak | None = None

        for address in tuple(self._known_addresses):
            service_info = bluetooth.async_last_service_info(
                self.hass, address, connectable=False
            )
            if service_info is None or not self._matches(service_info):
                continue
            if freshest is None or service_info.time > freshest.time:
                freshest = service_info

        if freshest is not None:
            self._async_consider_service_info(freshest)

        self._async_apply_timeout()

    @callback
    def _async_consider_service_info(
        self, service_info: bluetooth.BluetoothServiceInfoBleak
    ) -> None:
        """Use a matching cached/live advertisement as the newest observation."""
        seen_mono = service_info.time

        if (
            self._last_service_monotonic is not None
            and seen_mono <= self._last_service_monotonic
        ):
            return

        self._last_service_monotonic = seen_mono
        age = max(0.0, time.monotonic() - seen_mono)
        self.last_seen = dt_util.now() - timedelta(seconds=age)
        self.last_source = service_info.source

        # Startup safety: a replayed packet from before this integration started
        # may teach us the address, but it must not restore ON and create an
        # artificial ON->OFF / OFF->ON sequence after a Home Assistant restart.
        if seen_mono < self._started_monotonic:
            return

        changed = self.present is not True
        self.present = True
        if changed:
            _LOGGER.debug(
                "Beacon %s/%s/%s present via %s",
                self.uuid,
                self.major,
                self.minor,
                self.last_source,
            )
        self._async_notify_listeners()

    @callback
    def _async_apply_timeout(self) -> None:
        now_mono = time.monotonic()

        if self.present is True and self._last_service_monotonic is not None:
            if now_mono - self._last_service_monotonic >= self.timeout:
                self.present = False
                _LOGGER.debug(
                    "Beacon %s/%s/%s absent after %ss timeout",
                    self.uuid,
                    self.major,
                    self.minor,
                    self.timeout,
                )
                self._async_notify_listeners()
            return

        if self.present is None and now_mono - self._started_monotonic >= self.timeout:
            # First determinate state after startup: unavailable -> off.
            # This is intentionally not a meaningful FSM transition.
            self.present = False
            self._async_notify_listeners()
