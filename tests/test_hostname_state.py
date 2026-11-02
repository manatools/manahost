import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from manahost.hostname_state import HostnameStatus


class FakeIntrospectable:
    def __init__(self, xml):
        self._xml = xml
        self.calls = 0

    def Introspect(self):
        self.calls += 1
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

    def test_save_rejects_too_long_hostname(self):
        status = HostnameStatus()
        too_long = "a" * (HostnameStatus.HOSTNAME_MAX_LENGTH + 1)
        with mock.patch("manahost.hostname_state.dbus", object()):
            with self.assertRaises(ValueError):
                status.save({"hostname": too_long})

    def test_save_rejects_invalid_hostname_characters(self):
        status = HostnameStatus()
        with mock.patch("manahost.hostname_state.dbus", object()):
            with self.assertRaises(ValueError):
                status.save({"hostname": "Bad Hostname"})

    def test_writable_fields_are_cached_after_first_introspection(self):
        introspectable = FakeIntrospectable(
            "<node><interface name='org.freedesktop.hostname1'><method name='SetHostname' /></interface></node>"
        )
        fake_bus = FakeBus()

        def fake_interface(proxy, iface):
            if iface == "org.freedesktop.DBus.Introspectable":
                return introspectable
            raise AssertionError(f"Unsupported interface {iface}")

        fake_dbus = SimpleNamespace(SystemBus=lambda: fake_bus, Interface=fake_interface)
        with mock.patch("manahost.hostname_state.dbus", fake_dbus):
            status = HostnameStatus()
            self.assertEqual(status.writable_fields(), {"hostname"})
            self.assertEqual(status.writable_fields(), {"hostname"})
        self.assertEqual(introspectable.calls, 1)

    def test_localized_help_uses_shared_python_manatools_catalog(self):
        if shutil.which("msgfmt") is None:
            self.skipTest("msgfmt not available")

        project_root = Path(__file__).resolve().parents[1]
        shared_root = project_root.parent / "python-manatools"
        self.assertTrue((shared_root / "po" / "it.po").is_file())

        with tempfile.TemporaryDirectory() as temp_dir:
            locale_root = Path(temp_dir)
            message_dir = locale_root / "it" / "LC_MESSAGES"
            message_dir.mkdir(parents=True)

            subprocess.run(
                ["msgfmt", str(project_root / "po" / "it.po"), "-o", str(message_dir / "manahost.mo")],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            subprocess.run(
                ["msgfmt", str(shared_root / "po" / "it.po"), "-o", str(message_dir / "python-manatools.mo")],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            env = os.environ.copy()
            pythonpath = [str(project_root), str(shared_root)]
            existing = env.get("PYTHONPATH")
            if existing:
                pythonpath.append(existing)
            env["PYTHONPATH"] = os.pathsep.join(pythonpath)

            result = subprocess.run(
                [sys.executable, "-m", "manahost.app", "--locales-dir", str(locale_root), "--help"],
                cwd=str(project_root),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: manahost [opzioni]", result.stdout)
        self.assertIn("opzioni:", result.stdout)
        self.assertIn("avvia usando il backend Gtk", result.stdout)
        self.assertIn("mostra questo messaggio di aiuto ed esce", result.stdout)


if __name__ == "__main__":
    unittest.main()
