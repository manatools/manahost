# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
manahost is a graphical hostname configuration tool based on ManaTools AUI python

License: GPLv3

Author:  Angelo Naselli <anaselli@linux.it>

@package manahost
'''
"""Graphical dialog used to edit readable hostname data with a libYui BaseDialog."""

import gettext
import logging
import re

from manatools.ui import common as ui
from manatools.ui import basedialog
from manatools.ui import helpdialog

from . import APP_DISPLAY_NAME
from .helpinfo import HostnameHelpInfo
from .hostname_state import HostnameStatus

_ = gettext.gettext
logger = logging.getLogger("manahost.dialog")


class HostnameDialog(basedialog.BaseDialog):
    """Simple hostname editor that exposes mutable systemd hostname fields."""
    _LABEL_COLUMN_WIDTH = 220
    _ICON_PREVIEW_SIZE = 24
    _ICON_FALLBACK_NAME = "computer"
    _TOOLTIPS = {
        "hostname": _("Transient hostname for the current running system."),
        "static_hostname": _("Persistent hostname stored on disk and used at boot."),
        "pretty_hostname": _("Human-friendly hostname used in desktop and shell views."),
        "icon_name": _("Desktop icon name representing the machine class."),
        "chassis": _("Hardware chassis type (desktop, laptop, vm, server, etc.)."),
    }

    def __init__(self, status):
        super().__init__(
            title=_(APP_DISPLAY_NAME),
            icon="manahost",
            dialogType=basedialog.DialogType.MAIN,
            minWidth=700,
            minHeight=260,
        )
        self._status = status
        self._available_writes = status.writable_fields()
        self._initial_values = status.editable_values()
        self._editable_fields = {}
        self._readonly_fields = {}
        self._chassis_edit_toggle = None
        self._icon_preview_button = None
        self._save_button = None

    def UIlayout(self, layout):
        """Build the dialog widgets and form fields."""
        self._build_section(layout, _("System hostname"), [
            (_("Hostname"), "hostname", True),
            (_("Static hostname"), "static_hostname", True),
            (_("Pretty hostname"), "pretty_hostname", True),
            (_("Icon name"), "icon_name", True),
            (_("Chassis"), "chassis", True),
        ])

        self._build_readonly_section(layout, _("System information"), [
            (_("Kernel"), "kernel_release"),
            (_("Operating system"), "operating_system"),
            (_("Hardware vendor"), "hardware_vendor"),
            (_("Hardware model"), "hardware_model"),
            (_("Hardware SKU"), "hardware_sku"),
            (_("Hardware version"), "hardware_version"),
            (_("Firmware version"), "firmware_version"),
            (_("Firmware date"), "firmware_date"),
            (_("Machine ID"), "machine_id"),
            (_("Boot ID"), "boot_id"),
        ])

        action_row = self.factory.createHBox(layout)
        self.factory.createHStretch(action_row)
        help_button = self.factory.createIconButton(action_row, "help-browser", _("&Help"))
        help_button.setHelpText(_("Open help with field descriptions and usage notes."))
        self.eventManager.addWidgetEvent(help_button, self._on_help)
        self.factory.createHSpacing(action_row, 8)
        about_button = self.factory.createIconButton(action_row, "help-about", _("&About"))
        about_button.setHelpText(_("Show application information, version and credits."))
        self.eventManager.addWidgetEvent(about_button, self._on_about)
        self.factory.createHSpacing(action_row, 8)
        self._save_button = self.factory.createIconButton(action_row, "document-save", _("&Save"))
        self._save_button.setEnabled(False)
        self._save_button.setHelpText(_("Save modified hostname values to the system."))
        self.eventManager.addWidgetEvent(self._save_button, self._on_save)
        self.factory.createHSpacing(action_row, 8)
        close_button = self.factory.createIconButton(action_row, "application-exit", _("&Close"))
        close_button.setHelpText(_("Close this dialog without applying new changes."))
        self.eventManager.addWidgetEvent(close_button, self._on_close)

        unsupported = sorted(set(self._status.editable_fields) - set(self._available_writes))
        if unsupported:
            logger.info("The following hostname fields are not writable on this system: %s", unsupported)

    def _build_section(self, layout, title, rows):
        """Create a simple editable form using aligned label-plus-entry rows."""
        title_label = self.factory.createLabel(layout, title)
        title_label.setEnabled(True)
        self.factory.createVSpacing(layout, 4)
        for label_text, field_name, editable in rows:
            row, value_parent = self._create_form_row(layout, label_text)
            if editable:
                field = self.factory.createInputField(value_parent, "")
                field.setValue(getattr(self._status, field_name, "") or "")
                field.setEnabled(True)
                field.setStretchable(basedialog.yui.YUIDimension.YD_HORIZ, True)
                field.setWeight(basedialog.yui.YUIDimension.YD_HORIZ, 1)
                max_length = self._status.field_max_length(field_name)
                if hasattr(field, "setInputMaxLength"):
                    field.setInputMaxLength(max_length)
                tooltip_text = self._TOOLTIPS.get(field_name)
                if tooltip_text:
                    field.setHelpText(tooltip_text)
                self._editable_fields[field_name] = field
                self.eventManager.addWidgetEvent(field, self._on_field_change, sendWidget=True)
                if field_name == "icon_name":
                    self._add_icon_preview(value_parent)
                if field_name == "chassis":
                    self._add_chassis_edit_toggle(layout)
            else:
                value = getattr(self._status, field_name, "") or "-"
                value_label = self.factory.createLabel(value_parent, value, isOutputField=True)
                value_label.setStretchable(basedialog.yui.YUIDimension.YD_HORIZ, True)
                value_label.setWeight(basedialog.yui.YUIDimension.YD_HORIZ, 1)
            row.setStretchable(basedialog.yui.YUIDimension.YD_HORIZ, True)

    def _build_readonly_section(self, layout, title, rows):
        """Create a read-only summary section to keep the form readable."""
        self.factory.createVSpacing(layout, 8)
        title_label = self.factory.createLabel(layout, title)
        title_label.setEnabled(True)
        self.factory.createVSpacing(layout, 4)
        for label_text, field_name in rows:
            row, value_parent = self._create_form_row(layout, label_text)
            value = getattr(self._status, field_name, "") or "-"
            value_label = self.factory.createLabel(value_parent, str(value), isOutputField=True)
            value_label.setStretchable(basedialog.yui.YUIDimension.YD_HORIZ, True)
            value_label.setWeight(basedialog.yui.YUIDimension.YD_HORIZ, 1)
            self._readonly_fields[field_name] = value_label
            row.setStretchable(basedialog.yui.YUIDimension.YD_HORIZ, True)

    def _create_form_row(self, layout, label_text):
        """Create an aligned row with a fixed-width label column and a flexible value column."""
        row = self.factory.createHBox(layout)

        label_column = self.factory.createMinSize(row, self._LABEL_COLUMN_WIDTH, 1)
        label_column.setWeight(basedialog.yui.YUIDimension.YD_HORIZ, 30)
        label_align = self.factory.createLeft(label_column)
        label_value = f"{label_text}:" if label_text else ""
        self.factory.createLabel(label_align, label_value)

        self.factory.createHSpacing(row, 8)

        value_parent = self.factory.createHBox(row)
        value_parent.setStretchable(basedialog.yui.YUIDimension.YD_HORIZ, True)
        value_parent.setWeight(basedialog.yui.YUIDimension.YD_HORIZ, 70)
        return row, value_parent

    @staticmethod
    def _is_blank(value):
        """Return True if the provided string is empty after trimming spaces."""
        return not str(value or "").strip()

    def _chassis_toggle_default(self):
        """Compute default chassis-edit toggle according to current data."""
        current_chassis = getattr(self._status, "chassis", "")
        return self._is_blank(current_chassis)

    def _add_chassis_edit_toggle(self, layout):
        """Create the checkbox controlling whether the chassis field can be edited."""
        toggle_row, toggle_parent = self._create_form_row(layout, "")
        self._chassis_edit_toggle = self.factory.createCheckBox(
            toggle_parent,
            _("Allow editing chassis manually"),
            self._chassis_toggle_default(),
        )
        self._chassis_edit_toggle.setHelpText(
            _("Enable only if automatic chassis detection is missing or incorrect.")
        )
        self._chassis_edit_toggle.setNotify(True)
        self.eventManager.addWidgetEvent(self._chassis_edit_toggle, self._on_chassis_toggle)
        toggle_row.setStretchable(basedialog.yui.YUIDimension.YD_HORIZ, True)
        self._apply_chassis_edit_policy()

    def _apply_chassis_edit_policy(self):
        """Apply chassis editability rules based on write support and user toggle."""
        chassis_field = self._editable_fields.get("chassis")
        if chassis_field is None:
            return
        writable = "chassis" in self._available_writes
        if self._chassis_edit_toggle is None:
            chassis_field.setEnabled(writable)
            return

        if not writable:
            self._chassis_edit_toggle.setEnabled(False)
            chassis_field.setEnabled(False)
            return

        self._chassis_edit_toggle.setEnabled(True)
        chassis_field.setEnabled(bool(self._chassis_edit_toggle.value()))

    def _on_chassis_toggle(self, owner=None, event=None):
        """Apply manual chassis-edit toggle state to the field."""
        self._apply_chassis_edit_policy()

    def _on_field_change(self, owner=None, widget=None, event=None):
        """Enable saving only when the user actually changes a value."""
        self._sync_icon_preview()
        if self._save_button is None:
            return
        self._save_button.setEnabled(self._has_changes())

    def _add_icon_preview(self, parent):
        """Create a small live preview next to the icon-name field."""
        self.factory.createHSpacing(parent, 8)
        icon_box = self.factory.createMinSize(parent, self._ICON_PREVIEW_SIZE, self._ICON_PREVIEW_SIZE)
        icon_box.setWeight(basedialog.yui.YUIDimension.YD_HORIZ, 0)
        self._icon_preview_button = self.factory.createIconButton(
            icon_box,
            self._icon_preview_name(),
            _("Preview"),
        )
        self._icon_preview_button.setEnabled(False)
        self._icon_preview_button.setHelpText(_("Preview of the icon selected in Icon name."))

    def _icon_preview_name(self):
        """Return the icon name to show in the preview widget."""
        field = self._editable_fields.get("icon_name")
        icon_name = field.value().strip() if field is not None else ""
        if icon_name:
            return icon_name
        chassis_name = self._icon_fallback_chassis_name()
        if chassis_name:
            return f"{self._ICON_FALLBACK_NAME}-{chassis_name}"
        return self._ICON_FALLBACK_NAME

    def _icon_fallback_chassis_name(self):
        """Return normalized chassis value usable in the fallback icon name."""
        field = self._editable_fields.get("chassis")
        raw_value = field.value() if field is not None else getattr(self._status, "chassis", "")
        normalized = str(raw_value or "").strip().lower().replace("_", "-")
        normalized = re.sub(r"[^a-z0-9-]+", "-", normalized)
        normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
        return normalized

    def _sync_icon_preview(self):
        """Update the icon preview to reflect current icon-name input."""
        if self._icon_preview_button is None:
            return
        try:
            self._icon_preview_button.setIcon(self._icon_preview_name())
        except Exception:
            logger.exception("Unable to update icon preview")

    def _has_changes(self):
        """Return True when at least one editable field differs from the original snapshot."""
        for key, widget in self._editable_fields.items():
            current_value = widget.value().strip()
            original_value = str(self._initial_values.get(key, "")).strip()
            if current_value != original_value:
                return True
        return False

    def _on_save(self, owner=None, event=None):
        """Persist edited values and refresh the internal snapshot."""
        changes = {}
        for key, widget in self._editable_fields.items():
            new_value = widget.value().strip()
            original_value = str(self._initial_values.get(key, "")).strip()
            if new_value != original_value:
                changes[key] = new_value

        if not changes:
            self._save_button.setEnabled(False)
            return

        try:
            self._status.save(changes)
            self._reload_from_system()
            self._save_button.setEnabled(False)
            logger.info("Saved hostname changes: %s", changes)
        except ValueError as exc:
            logger.warning("Hostname input validation failed: %s", exc)
            ui.warningMsgBox({
                "title": _("Invalid input"),
                "text": _("One or more fields contain invalid values.\n\nDetails: %s") % str(exc),
            })
        except Exception as exc:
            logger.exception("Unexpected error while saving hostname changes")
            ui.warningMsgBox({
                "title": _("Save failed"),
                "text": _("Unable to save hostname values through D-Bus.\n\nDetails: %s") % str(exc),
            })

    def _reload_from_system(self):
        """Reload hostname values from D-Bus after a successful write."""
        try:
            self._status = HostnameStatus.load()
        except Exception as exc:
            logger.exception("Hostname status reload failed after save")
            ui.warningMsgBox({
                "title": _("Reload failed"),
                "text": _("Changes were sent, but reloading current system values failed.\n\nDetails: %s") % str(exc),
            })
            self._initial_values = {
                key: widget.value().strip()
                for key, widget in self._editable_fields.items()
            }
            return

        for key, widget in self._editable_fields.items():
            widget.setValue(getattr(self._status, key, "") or "")

        for key, widget in self._readonly_fields.items():
            value = getattr(self._status, key, "") or "-"
            widget.setValue(str(value))

        self._available_writes = self._status.writable_fields()
        self._initial_values = self._status.editable_values()
        if self._chassis_edit_toggle is not None:
            self._chassis_edit_toggle.setValue(self._chassis_toggle_default())
        self._apply_chassis_edit_policy()
        self._sync_icon_preview()

    def _on_close(self, owner=None, event=None):
        """Close the dialog by stopping the event loop."""
        self.ExitLoop()

    def _on_about(self, owner=None, event=None):
        """Open the project About dialog."""
        try:
            ui.AboutDialog(
                dialog_mode=ui.AboutDialogMode.TABBED,
                size={"width": 640, "height": 300},
            )
        except Exception:
            logger.exception("Unable to open About dialog")

    def _on_help(self, owner=None, event=None):
        """Open the contextual Help dialog describing hostname fields."""
        try:
            info = HostnameHelpInfo()
            dialog = helpdialog.HelpDialog(info, minWidth=640, minHeight=300)
            dialog.run()
        except Exception:
            logger.exception("Unable to open Help dialog")
