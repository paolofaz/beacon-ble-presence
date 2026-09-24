"""Minimal iBeacon parser used by Beacon BLE Presence."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak

from .const import APPLE_MFR_ID, IBEACON_PREFIX


@dataclass(frozen=True, slots=True)
class ParsedIBeacon:
    """The iBeacon identity fields we care about."""

    uuid: str
    major: int
    minor: int


def parse_ibeacon(service_info: BluetoothServiceInfoBleak) -> ParsedIBeacon | None:
    """Parse UUID/Major/Minor from an Apple iBeacon manufacturer payload."""
    payload = service_info.manufacturer_data.get(APPLE_MFR_ID)
    if payload is None or len(payload) < 23 or not payload.startswith(IBEACON_PREFIX):
        return None

    try:
        uuid = str(UUID(bytes=bytes(payload[2:18])))
    except (ValueError, AttributeError):
        return None

    major = int.from_bytes(payload[18:20], byteorder="big", signed=False)
    minor = int.from_bytes(payload[20:22], byteorder="big", signed=False)
    return ParsedIBeacon(uuid=uuid, major=major, minor=minor)
