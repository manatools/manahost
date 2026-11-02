# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
manahost is a graphical hostname configuration tool based on ManaTools AUI python

License: GPLv3

Author:  Angelo Naselli <anaselli@linux.it>

@package manahost
'''

"""System hostname configuration tool for ManaTools."""

from pathlib import Path


def N_(message):
    """Mark a string for translation without translating at import time."""
    return message


APP_NAME = "manahost"
__version__ = "0.1.0"
APP_ICON_NAME = APP_NAME
APP_ICON_PATH = str(Path(__file__).resolve().parent / "resources" / "manahost.svg")
APP_DISPLAY_NAME = N_("manahost - ManaTools hostname control")
APP_LICENSE = "GPL-3-or-later"
APP_DESCRIPTION = (
    N_("Graphical hostname control tool using org.freedesktop.hostname1 "
    "with a backend-independent ManaTools Abstract User Interface."
    )
)

APP_CLI_DESCRIPTION = N_("Manage the system hostname through the systemd hostname1 API.")
APP_PROJECT_URL = "https://github.com/manatools/manahost"
APP_MANATOOLS_URL = "https://github.com/manatools/python-manatools"

from .app import main

__all__ = [
    "APP_NAME",
    "APP_ICON_NAME",
    "APP_ICON_PATH",
    "APP_DISPLAY_NAME",
    "APP_LICENSE",
    "APP_DESCRIPTION",
    "APP_CLI_DESCRIPTION",
    "APP_PROJECT_URL",
    "APP_MANATOOLS_URL",
    "__version__",
    "main",
]
