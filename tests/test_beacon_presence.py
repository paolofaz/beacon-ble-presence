"""Regression tests for passive iBeacon tracking without an HA installation."""

import importlib.util
from datetime import datetime, timezone
from pathlib import Path
import sys
import types
from unittest import TestCase, mock
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "beacon_ble_presence"
TEST_UUID = "12345678-1234-1234-1234-123456789abc"


def advertisement(address, seen, major=1, minor=2, source="esphome-proxy"):
    payload = (
        b"\x02\x15" + UUID(TEST_UUID).bytes
        + major.to_bytes(2, "big") + minor.to_bytes(2, "big") + b"\xc5"
    )
    return types.SimpleNamespace(
        address=address,
        time=seen,
        source=source,
        manufacturer_data={0x004C: payload},
    )


def load_modules():
    """Load real parser/coordinator, replacing only HA runtime APIs."""
    base = "beacon_ble_presence_test_package"
    package = types.ModuleType(base)
    package.__path__ = [str(ROOT)]
    ha = types.ModuleType("homeassistant")
    components = types.ModuleType("homeassistant.components")
    bluetooth = types.ModuleType("homeassistant.components.bluetooth")
    bluetooth.BluetoothServiceInfoBleak = object
    bluetooth.BluetoothChange = object
    bluetooth.BluetoothScanningMode = types.SimpleNamespace(PASSIVE="passive")
    bluetooth.BluetoothCallbackReplay = types.SimpleNamespace(NEWEST_FIRST="newest")
    bluetooth.registered = []
    bluetooth.history = {}
    bluetooth.BluetoothCallbackMatcher = dict

    def register(*args, **kwargs):
        bluetooth.registered.append((args, kwargs))
        return lambda: None

    bluetooth.async_register_callback = register
    bluetooth.async_last_service_info = (
        lambda hass, address, *, connectable: bluetooth.history.get(address)
    )
    components.bluetooth = bluetooth
    ha.components = components

    match = types.ModuleType("homeassistant.components.bluetooth.match")
    match.BluetoothCallbackMatcher = dict
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    core.callback = lambda func: func

    helpers = types.ModuleType("homeassistant.helpers")
    event = types.ModuleType("homeassistant.helpers.event")
    event.async_track_time_interval = lambda hass, callback, interval: lambda: None
    helpers.event = event

    util = types.ModuleType("homeassistant.util")
    dt = types.ModuleType("homeassistant.util.dt")
    dt.now = lambda: datetime(2026, 10, 20, tzinfo=timezone.utc)
    util.dt = dt

    modules = {
        base: package,
        "homeassistant": ha,
        "homeassistant.components": components,
        "homeassistant.components.bluetooth": bluetooth,
        "homeassistant.components.bluetooth.match": match,
        "homeassistant.core": core,
        "homeassistant.helpers": helpers,
        "homeassistant.helpers.event": event,
        "homeassistant.util": util,
        "homeassistant.util.dt": dt,
    }

    with mock.patch.dict(sys.modules, modules):
        def load(short):
            name = base + "." + short
            spec = importlib.util.spec_from_file_location(name, ROOT / (short + ".py"))
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
            return mod

        const = load("const")
        parser = load("parser")
        coord = load("coordinator")
    return const, parser, coord, bluetooth


def make_coordinator(module, *, major=1, minor=2, timeout=180, time_start=1000.0):
    entry = types.SimpleNamespace(
        data={"uuid": TEST_UUID, "major": major, "minor": minor,
              "presence_timeout": timeout, "name": "My beacon"},
        options={},
        callbacks=[],
    )
    entry.async_on_unload = entry.callbacks.append
    with mock.patch.object(module.time, "monotonic", return_value=time_start):
        coordinator = module.BeaconPresenceCoordinator(object(), entry)
    return coordinator, entry


class BeaconParserTests(TestCase):
    def test_valid_payload_uuid_major_minor(self):
        _, parser, _, _ = load_modules()
        parsed = parser.parse_ibeacon(advertisement("AA", 1000))
        self.assertEqual(parsed.uuid, TEST_UUID)
        self.assertEqual((parsed.major, parsed.minor), (1, 2))

    def test_malformed_and_missing_manufacturer_data(self):
        _, parser, _, _ = load_modules()
        info = advertisement("AA", 1000)
        info.manufacturer_data = {}
        self.assertIsNone(parser.parse_ibeacon(info))
        info.manufacturer_data = {0x004C: b"\x02\x15\x00"}
        self.assertIsNone(parser.parse_ibeacon(info))
        info.manufacturer_data = {0x004C: b"\x02\x16" + bytes(21)}
        self.assertIsNone(parser.parse_ibeacon(info))


class BeaconCoordinatorTests(TestCase):
    def test_matches_only_correct_beacon(self):
        _, _, m, _ = load_modules()
        c, _ = make_coordinator(m)
        self.assertTrue(c._matches(advertisement("AA", 1000)))
        self.assertFalse(c._matches(advertisement("AA", 1000, major=3)))
        self.assertFalse(c._matches(advertisement("AA", 1000, minor=4)))

    def test_remembers_at_most_128_mac_addresses(self):
        _, _, m, _ = load_modules()
        c, _ = make_coordinator(m)
        with mock.patch.object(m.time, "monotonic", return_value=2000):
            for idx in range(300):
                c._async_bluetooth_event(
                    advertisement(f"AA:{idx:04X}", 1995 + idx / 1000), None
                )
        self.assertEqual(len(c._known_addresses), m.MAX_KNOWN_ADDRESSES)
        self.assertIn("AA:012B", c._known_addresses)
        self.assertNotIn("AA:0000", c._known_addresses)

    def test_prunes_stale_addresses(self):
        _, _, m, _ = load_modules()
        c, _ = make_coordinator(m)
        with mock.patch.object(m.time, "monotonic", return_value=1001):
            c._async_bluetooth_event(advertisement("STATIC", 1001), None)
        self.assertIn("STATIC", c._known_addresses)
        with mock.patch.object(m.time, "monotonic", return_value=4700):
            c._prune_addresses(4700)
        self.assertEqual(c._known_addresses, {})

    def test_no_false_present_from_pre_restart_cache(self):
        _, _, m, _ = load_modules()
        c, _ = make_coordinator(m, time_start=1000)
        with mock.patch.object(m.time, "monotonic", return_value=1001):
            c._async_bluetooth_event(advertisement("AA", 999), None)
        self.assertIsNone(c.present)
        self.assertIn("AA", c._known_addresses)
        with mock.patch.object(m.time, "monotonic", return_value=1002):
            c._async_bluetooth_event(advertisement("AA", 1002), None)
        self.assertTrue(c.present)

    def test_only_presence_changes_trigger_updates(self):
        _, _, m, bt = load_modules()
        c, _ = make_coordinator(m, time_start=1000, timeout=180)
        updates = []
        c.async_add_listener(lambda: updates.append(c.present))
        with mock.patch.object(m.time, "monotonic", return_value=1001):
            c._async_bluetooth_event(advertisement("AA", 1001), None)
        self.assertEqual(updates, [True])

        for now in range(1006, 1057, 5):
            with mock.patch.object(m.time, "monotonic", return_value=now):
                bt.history["AA"] = advertisement("AA", now)
                c._async_refresh_from_bluetooth_cache()
        self.assertEqual(updates, [True])
        self.assertIsNotNone(c.last_seen)
        self.assertEqual(c._last_service_monotonic, 1056)

        with mock.patch.object(m.time, "monotonic", return_value=1066):
            bt.history["AA"] = advertisement("AA", 1066)
            c._async_refresh_from_bluetooth_cache()
        self.assertEqual(updates, [True])

        with mock.patch.object(m.time, "monotonic", return_value=1247):
            c._async_apply_timeout()
        self.assertEqual(updates, [True, False])
        self.assertFalse(c.present)

    def test_initial_absent_after_timeout(self):
        _, _, m, _ = load_modules()
        c, _ = make_coordinator(m, time_start=1000, timeout=180)
        with mock.patch.object(m.time, "monotonic", return_value=1180):
            c._async_apply_timeout()
        self.assertFalse(c.present)

    def test_stale_packet_never_sets_present(self):
        _, _, m, _ = load_modules()
        c, _ = make_coordinator(m, time_start=1000, timeout=180)
        with mock.patch.object(m.time, "monotonic", return_value=1200):
            c._async_bluetooth_event(advertisement("AA", 1001), None)
        self.assertIsNone(c.present)

    def test_passive_registration_and_cleanup_callbacks(self):
        _, _, m, bt = load_modules()
        c, entry = make_coordinator(m)
        import asyncio
        asyncio.run(c.async_start())
        self.assertEqual(len(bt.registered), 1)
        args, kwargs = bt.registered[0]
        self.assertEqual(args[3], "passive")
        self.assertEqual(kwargs["replay"], "newest")
        self.assertEqual(len(entry.callbacks), 2)

    def test_configuration_uuid_and_ids_are_read_only(self):
        _, _, m, _ = load_modules()
        entry = types.SimpleNamespace(
            data={"name": "Beacon 1", "uuid": TEST_UUID, "major": 1,
                  "minor": 2, "presence_timeout": 180},
            options={"presence_timeout": 90},
        )
        before_data, before_options = dict(entry.data), dict(entry.options)
        c = m.BeaconPresenceCoordinator(object(), entry)
        self.assertEqual((c.uuid, c.major, c.minor), (TEST_UUID, 1, 2))
        self.assertEqual(c.timeout, 90)
        self.assertEqual(entry.data, before_data)
        self.assertEqual(entry.options, before_options)
