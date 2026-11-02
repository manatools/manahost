# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
manahost is a graphical hostname configuration tool based on ManaTools AUI python

License: GPLv3

Author:  Angelo Naselli <anaselli@linux.it>

@package manahost
'''
"""Help content for the manahost dialog."""

import gettext

import manatools.basehelpinfo as helpdata

_ = gettext.gettext


class HostnameHelpInfo(helpdata.HelpInfoBase):
    """HelpInfo implementation describing hostname fields and editing policy."""

    def __init__(self):
        super().__init__()
        home_lnk = f"<b>{self._format_link(_('Go to index'), 'home')}</b>"
        fields_lnk = f"<b>{self._format_link(_('Editable fields'), 'editable_fields')}</b>"
        chassis_lnk = f"<b>{self._format_link(_('Chassis field policy'), 'chassis_policy')}</b>"
        apply_lnk = f"<b>{self._format_link(_('Applying changes'), 'apply_changes')}</b>"

        index = "<ul>%s</ul>" % "".join(
            f"<li>{item}</li>"
            for item in (fields_lnk, chassis_lnk, apply_lnk)
        )

        self.text = {
            "home": "<h1>manahost</h1>%s<br>%s" % (
                _(
                    "This tool reads and writes hostname information through "
                    "org.freedesktop.hostname1 on D-Bus."
                ),
                index,
            ),
            "editable_fields": "<h1>%s</h1>%s<br>%s" % (
                _("Editable fields"),
                _(
                    "<ul>"
                    "<li><b>Hostname</b>: transient runtime hostname. This property is the actual hostname configured in the kernel.<br>" \
                    "It can be different from the static hostname. This property is never empty.</li>"
                    "<li><b>Static hostname</b>: persistent hostname saved on disk and configured in /etc/hostname.</li>"
                    "<li><b>Pretty hostname</b>: user-friendly display name. This property exposes the pretty hostname which is a free-form UTF-8 hostname for presentation to the user.<br>" \
                    "User interfaces should ensure that the pretty hostname and the static hostname stay in sync. E.g. when the former is <i>Lennart’s Computer</i> the latter should be <i>lennarts-computer</i>.</li>"
                    "<li><b>Icon name</b>: desktop icon identifier for the machine. This property exposes the icon name following the XDG icon naming specification.<br>" \
                    "If not set, information such as the chassis type (see below) is used to find a suitable fallback icon name (i.e. <i>computer-laptop</i> vs. <i>computer-desktop</i> is picked based on the chassis information). If no such data is available, the empty string is returned.<br>" \
                    "In that case an application should fall back to a replacement icon, for example <i>computer</i>.<br>" \
                    "If this property is set to the empty string, the automatic fallback name selection is enabled again.</li>"
                    "<li><b>Chassis</b>: hardware type (desktop, laptop, vm, server, etc.). This property exposes a chassis type, one of the currently defined chassis types.<br>" \
                    "Note that in most cases the chassis type will be determined automatically from DMI/SMBIOS/ACPI firmware information.<br>" \
                    "Writing to this setting is hence useful only to override misdetected chassis types, or to configure the chassis type if it could not be auto-detected.<br>" \
                    "Set this property to the empty string to reenable the automatic detection of the chassis type from firmware information.</li>"
                    "</ul>"
                ),
                home_lnk,
            ),
            "chassis_policy": "<h1>%s</h1>%s<br>%s" % (
                _("Chassis field policy"),
                _(
                    "Chassis is usually auto-detected correctly by the system. "
                    "For safety, manual editing is disabled by default when a value "
                    "already exists. If chassis is empty, manual editing is enabled "
                    "by default through the dedicated checkbox."
                ),
                home_lnk,
            ),
            "apply_changes": "<h1>%s</h1>%s<br>%s" % (
                _("Applying changes"),
                _(
                    "After pressing Save, changes are sent through D-Bus and the "
                    "dialog reloads values from the running system to show the "
                    "effective state."
                ),
                home_lnk,
            ),
        }

    @staticmethod
    def _format_link(description, url):
        """Return an HTML link for HelpDialog navigation."""
        return f'<a href="{url}">{description}</a>'

    def show(self, info_to_show):
        """Return the requested section by id."""
        return self.text.get(info_to_show, "")

    def home(self):
        """Return the home page section."""
        return self.text["home"]
