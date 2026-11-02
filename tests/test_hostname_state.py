import unittest
from types import SimpleNamespace
from unittest import mock

from manahost.hostname_state import HostnameStatus


class FakeIntrospectable:
    def __init__(self, xml):
        self._xml = xml

    def Introspect(self):
        return self._xml


class FakeProperties:
    def __init__(self, values):
        self._values = values

    def GetAll(self, interface):
        return self._values


class FakeHostnameInterface:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def _call(value, interactive):
            self.calls.append((name, value, interactive))
        return _call


class FakeBus:
    def __init__(self):
        self.proxy = object()

    def get_object(self, service, path):
        return object()


class HostnameStatusTests(unittest.TestCase):
    def test_normalize_machine_id_converts_bytes_to_hex(self):
        raw = [8, 223, 36, 197, 254, 236, 64, 241, 181, 112, 204, 234, 86, 1, 242, 225]
        self.assertEqual(
            HostnameStatus._normalize_machine_id(raw),
            "08df24c5feec40f1b570ccea5601f2e1",
        )

    def test_load_requires_python_dbus(self):
        with mock.patch("manahost.hostname_state.dbus", None):
            with self.assertRaises(RuntimeError):
                HostnameStatus.load()

    def test_load_reads_values_from_dbus(self):
        values = {
            "Hostname": "gandalf",
            "StaticHostname": "gandalf",
            "PrettyHostname": "Gandalf",
            "KernelRelease": "Linux 6.18.55-desktop-1.mga10",
            "OperatingSystemPrettyName": "Mageia 10",
            "MachineID": [8, 223, 36, 197, 254, 236, 64, 241, 181, 112, 204, 234, 86, 1, 242, 225],
            "BootID": [103, 217, 246, 71, 179, 97, 73, 7, 178, 193, 49, 124, 11, 190, 14, 108],
        }
        fake_hostname = FakeHostnameInterface()
        fake_bus = FakeBus()

        def fake_interface(proxy, iface):
            if iface == "org.freedesktop.DBus.Properties":
                return FakeProperties(values)
            if iface == "org.freedesktop.DBus.Introspectable":
                return FakeIntrospectable(
                    "<node><interface name='org.freedesktop.hostname1'><method name='SetHostname' /></interface></node>"
                )
            if iface == "org.freedesktop.hostname1":
                return fake_hostname
            raise AssertionError(f"Unsupported interface {iface}")

        fake_dbus = SimpleNamespace(SystemBus=lambda: fake_bus, Interface=fake_interface)
        with mock.patch("manahost.hostname_state.dbus", fake_dbus):
            status = HostnameStatus.load()
        self.assertEqual(status.source, "dbus")
        self.assertEqual(status.hostname, "gandalf")
        self.assertEqual(status.pretty_hostname, "Gandalf")
        self.assertEqual(status.operating_system, "Mageia 10")
        self.assertEqual(status.machine_id, "08df24c5feec40f1b570ccea5601f2e1")

    def test_writable_fields_and_save_respect_dbus_capabilities(self):
        fake_bus = FakeBus()
        fake_dbus = SimpleNamespace(
            SystemBus=lambda: fake_bus,
            Interface=lambda proxy, iface: FakeIntrospectable(
                "<node><interface name='org.freedesktop.hostname1'><method name='SetHostname' /></interface></node>"
            ),
        )
        with mock.patch("manahost.hostname_state.dbus", fake_dbus):
            status = HostnameStatus()
            self.assertEqual(status.writable_fields(), {"hostname"})
            with self.assertRaises(PermissionError):
                status.save({"hostname": "gandalf", "static_hostname": "other"})

    def test_save_uses_dbus_methods_only(self):
        fake_hostname = FakeHostnameInterface()
        fake_bus = FakeBus()

        def fake_interface(proxy, iface):
            if iface == "org.freedesktop.DBus.Introspectable":
                return FakeIntrospectable(
                    "<node><interface name='org.freedesktop.hostname1'>"
                    "<method name='SetHostname' /><method name='SetPrettyHostname' /></interface></node>"
                )
            if iface == "org.freedesktop.hostname1":
                return fake_hostname
            raise AssertionError(f"Unsupported interface {iface}")

        fake_dbus = SimpleNamespace(SystemBus=lambda: fake_bus, Interface=fake_interface)
        with mock.patch("manahost.hostname_state.dbus", fake_dbus):
            status = HostnameStatus()
            status.save({"hostname": "gandalf", "pretty_hostname": "Gandalf"})
        self.assertEqual(
            fake_hostname.calls,
            [("SetHostname", "gandalf", True), ("SetPrettyHostname", "Gandalf", True)],
        )


if __name__ == "__main__":
    unittest.main()
