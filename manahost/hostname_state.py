# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
manahost is a graphical hostname configuration tool based on ManaTools AUI python

License: GPLv3

Author:  Angelo Naselli <anaselli@linux.it>

@package manahost
'''

"""Helpers to read and write hostname information through systemd's hostname1 API."""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field

logger = logging.getLogger("manahost.hostname_state")

try:
    import dbus
except ImportError:  # pragma: no cover - optional dependency in minimal environments.
    dbus = None


def _as_text(value, default=""):
    """Convert D-Bus data to plain Python text, keeping the empty-string fallback."""
    if value is None:
        return default
    if isinstance(value, (list, tuple)):
        try:
            return "".join(f"{int(byte):02x}" for byte in value)
        except TypeError:
            return ", ".join(str(item) for item in value)
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (str, int, float)):
        return str(value)
    try:
        return str(value)
    except Exception:
        return default


def _to_date_string(raw_value):
    """Convert a systemd firmware timestamp into a concise ISO-like date."""
    try:
        timestamp = int(raw_value)
    except (TypeError, ValueError):
        return _as_text(raw_value)

    if timestamp <= 0:
        return ""

    try:
        dt = datetime.datetime.fromtimestamp(float(timestamp) / 1000000.0, tz=datetime.timezone.utc)
        return dt.strftime("%Y-%m-%d")
    except (OverflowError, OSError, ValueError):
        logger.exception("Failed to convert firmware timestamp %s", raw_value)
        return _as_text(raw_value)


@dataclass
class HostnameStatus:
    """Read-only snapshot of the system hostname and supporting metadata."""

    hostname: str = ""
    static_hostname: str = ""
    pretty_hostname: str = ""
    icon_name: str = ""
    chassis: str = ""
    deployment: str = ""
    location: str = ""
    default_hostname: str = ""
    hostname_source: str = ""
    kernel_name: str = ""
    kernel_release: str = ""
    kernel_version: str = ""
    operating_system: str = ""
    hardware_vendor: str = ""
    hardware_model: str = ""
    hardware_sku: str = ""
    hardware_version: str = ""
    firmware_version: str = ""
    firmware_date: str = ""
    machine_id: str = ""
    boot_id: str = ""
    source: str = "unavailable"
    editable_fields: dict = field(default_factory=lambda: {
        "hostname": "hostname",
        "static_hostname": "static_hostname",
        "pretty_hostname": "pretty_hostname",
        "icon_name": "icon_name",
        "chassis": "chassis",
        "deployment": "deployment",
        "location": "location",
    })

    @staticmethod
    def _normalize_machine_id(raw_value) -> str:
        """Render machine/boot identifiers as hexadecimal strings without DBus noise."""
        if raw_value is None:
            return ""
        if isinstance(raw_value, (list, tuple)):
            return "".join(f"{int(byte):02x}" for byte in raw_value)
        if isinstance(raw_value, (bytes, bytearray)):
            return raw_value.hex()
        return _as_text(raw_value)

    def writable_fields(self):
        """Return the subset of supported hostname fields that can be changed on this system.

        If the service cannot be introspected reliably, we prefer to keep the
        fields editable instead of silently locking the whole form. This matches
        the expected user experience: the dialog remains usable and any real
        write failure is reported through the save path with a logged exception.
        """
        supported = set(self.editable_fields)
        if dbus is None:
            return supported

        try:
            bus = dbus.SystemBus()
            proxy = bus.get_object("org.freedesktop.hostname1", "/org/freedesktop/hostname1")
            introspect = dbus.Interface(proxy, "org.freedesktop.DBus.Introspectable")
            xml = introspect.Introspect()
            allowed = set()
            method_map = {
                "SetHostname": "hostname",
                "SetStaticHostname": "static_hostname",
                "SetPrettyHostname": "pretty_hostname",
                "SetIconName": "icon_name",
                "SetChassis": "chassis",
                "SetDeployment": "deployment",
                "SetLocation": "location",
            }
            for method_name, field_name in method_map.items():
                if f"name='{method_name}'" in xml or f'<method name="{method_name}"' in xml:
                    allowed.add(field_name)
            if not allowed:
                logger.warning("hostname1 introspection did not expose writable methods; keeping supported fields editable")
                return supported
            logger.debug("Detected writable hostname fields: %s", sorted(allowed))
            return supported & allowed
        except Exception:
            logger.exception("Could not introspect hostname1 writable methods; keeping fields editable")
            return supported

    @classmethod
    def load(cls):
        """Load hostname metadata only from the systemd D-Bus API."""
        logger.debug("Loading hostname status from systemd hostname1 properties")
        if dbus is None:
            logger.error("python-dbus is not available: hostname status cannot be loaded")
            raise RuntimeError("python-dbus is required to load hostname metadata")
        try:
            return cls._load_from_dbus()
        except Exception as exc:
            logger.exception("D-Bus hostname query failed")
            raise RuntimeError("Unable to load hostname metadata from D-Bus") from exc

    @classmethod
    def _load_from_dbus(cls):
        """Read properties from org.freedesktop.hostname1 on the system bus."""
        bus = dbus.SystemBus()
        proxy = bus.get_object("org.freedesktop.hostname1", "/org/freedesktop/hostname1")
        properties = dbus.Interface(proxy, "org.freedesktop.DBus.Properties")
        values = properties.GetAll("org.freedesktop.hostname1")

        status = cls(source="dbus")
        mapping = {
            "Hostname": "hostname",
            "StaticHostname": "static_hostname",
            "PrettyHostname": "pretty_hostname",
            "IconName": "icon_name",
            "Chassis": "chassis",
            "Deployment": "deployment",
            "Location": "location",
            "DefaultHostname": "default_hostname",
            "HostnameSource": "hostname_source",
            "KernelName": "kernel_name",
            "KernelRelease": "kernel_release",
            "KernelVersion": "kernel_version",
            "OperatingSystemPrettyName": "operating_system",
            "HardwareVendor": "hardware_vendor",
            "HardwareModel": "hardware_model",
            "HardwareSKU": "hardware_sku",
            "HardwareVersion": "hardware_version",
            "FirmwareVersion": "firmware_version",
            "FirmwareDate": "firmware_date",
        }

        for property_name, attribute_name in mapping.items():
            raw_value = values.get(property_name)
            if raw_value is None:
                continue
            value = _as_text(raw_value)
            if property_name == "FirmwareDate":
                value = _to_date_string(raw_value)
            setattr(status, attribute_name, value)

        machine_id = values.get("MachineID")
        if machine_id is not None:
            status.machine_id = status._normalize_machine_id(machine_id)
        boot_id = values.get("BootID")
        if boot_id is not None:
            status.boot_id = status._normalize_machine_id(boot_id)

        return status

    def editable_values(self):
        """Return the values that can be edited by the user in the dialog."""
        writable = self.writable_fields()
        return {
            key: getattr(self, field_name, "")
            for key, field_name in self.editable_fields.items()
            if key in writable
        }

    def save(self, values):
        """Persist a dictionary of modified values using systemd hostname1 methods."""
        if not values:
            return self
        if dbus is None:
            logger.error("python-dbus is not available: hostname values cannot be saved")
            raise RuntimeError("python-dbus is required to save hostname metadata")

        writable = self.writable_fields()
        blocked = sorted(key for key in values if key not in writable)
        if blocked:
            logger.warning("Requested hostname writes are not supported on this system: %s", blocked)
            raise PermissionError(f"Write access to the following hostname fields is not available: {', '.join(blocked)}")

        try:
            bus = dbus.SystemBus()
            proxy = bus.get_object("org.freedesktop.hostname1", "/org/freedesktop/hostname1")
            hostname_if = dbus.Interface(proxy, "org.freedesktop.hostname1")
            for key, value in values.items():
                method_name = {
                    "hostname": "SetHostname",
                    "static_hostname": "SetStaticHostname",
                    "pretty_hostname": "SetPrettyHostname",
                    "icon_name": "SetIconName",
                    "chassis": "SetChassis",
                    "deployment": "SetDeployment",
                    "location": "SetLocation",
                }.get(key)
                if method_name is None:
                    continue
                getattr(hostname_if, method_name)(value, True)
                logger.info("Saved hostname property %s via D-Bus", key)
            return self
        except Exception as exc:
            logger.exception("D-Bus save failed")
            raise RuntimeError(f"Unable to save hostname metadata through D-Bus: {exc}") from exc
