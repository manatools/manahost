# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
manahost is a graphical hostname configuration tool based on ManaTools AUI python

License: GPLv3

Author:  Angelo Naselli <anaselli@linux.it>

@package manahost
'''

"""Application entry point for the hostname control dialog."""

import logging
import os
import sys
from importlib import metadata
import gettext

import manatools.aui.yui as MUI
from manatools.args import AppArgs

from . import (
    APP_CLI_DESCRIPTION,
    APP_DISPLAY_NAME,
    APP_ICON_NAME,
    APP_ICON_PATH,
    APP_DESCRIPTION,
    APP_LICENSE,
    APP_MANATOOLS_URL,
    APP_NAME,
    APP_PROJECT_URL,
    __version__,
)

_ = gettext.gettext
DEFAULT_LOCALE_DIR = "/usr/share/locale"

logger = logging.getLogger("manahost.app")


def _configure_i18n(locales_dir=DEFAULT_LOCALE_DIR):
    """Install gettext translations for the selected locale directory."""
    if hasattr(gettext, "bindtextdomain"):
        gettext.bindtextdomain(APP_NAME, locales_dir)
    if hasattr(gettext, "textdomain"):
        gettext.textdomain(APP_NAME)
    gettext.install(APP_NAME, localedir=locales_dir, names=("ngettext",))


def _extract_locales_dir(argv):
    """Extract --locales-dir value early, before argparse is created."""
    for index, arg in enumerate(argv):
        if arg.startswith("--locales-dir="):
            return arg.split("=", 1)[1]
        if arg == "--locales-dir" and index + 1 < len(argv):
            return argv[index + 1]
    return None


def _python_manatools_version() -> str:
    """Return the runtime python-manatools version for About metadata."""
    try:
        return metadata.version("python-manatools")
    except Exception:
        logger.exception("Unable to read python-manatools version from package metadata")
        return "unknown"


def _localize_legacy_appargs(parser):
    """Translate common AppArgs entries when using legacy python-manatools."""
    option_help_map = {
        "--help": _("show this help message and exit"),
        "--gtk": _("start using Gtk backend"),
        "--ncurses": _("start using ncurses backend"),
        "--qt": _("start using Qt backend"),
        "--locales-dir": _("directory containing localization strings (developer only)"),
        "--version": _("show application version and exit"),
    }
    if getattr(parser, "_optionals", None) is not None:
        parser._optionals.title = _("options")
    parser.usage = f"%(prog)s [{_('options')}]"
    for action in getattr(parser, "_actions", []):
        for option in action.option_strings:
            text = option_help_map.get(option)
            if text:
                action.help = text
                break


def _create_args_parser(locales_dir):
    """Build AppArgs parser, supporting both new and legacy python-manatools APIs."""
    try:
        return AppArgs(APP_NAME, localedir=locales_dir).parser
    except TypeError as exc:
        if "localedir" not in str(exc):
            raise
        logger.warning(
            "Installed python-manatools does not support AppArgs(localedir=...). "
            "Falling back to legacy AppArgs API."
        )
        parser = AppArgs(APP_NAME).parser
        _localize_legacy_appargs(parser)
        return parser


def _configure_logging(args) -> None:
    """Configure the logger according to the CLI switches and backend selection."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    if args.log_file:
        handler = logging.FileHandler(args.log_file, encoding="utf-8")
        level = logging.DEBUG if args.debug else logging.INFO
    elif args.logging or args.debug:
        handler = logging.StreamHandler()
        level = logging.DEBUG if args.debug else logging.INFO
    else:
        return

    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)
    root.setLevel(level)
    logger.info("Starting %s %s (log level: %s)", APP_NAME, __version__, logging.getLevelName(level))


def _configure_application_metadata() -> None:
    """Publish icon and About metadata to the active YUI backend."""
    app = MUI.YUI.app()
    author_email = "anaselli@linux.it"

    authors = (
        f"<h3>{_("Developers")}</h3>"
        "<ul>"
        f"<li>Angelo Naselli ({author_email})</li>"
        "</ul>"
    )
    information = (
        f"<h3>{_("Project Links")}</h3>"
        "<ul>"
        f"<li><b>manahost: </b><a href='{APP_PROJECT_URL}'>{APP_PROJECT_URL}</a></li>"
        f"<li><b>python-manatools: </b><a href='{APP_MANATOOLS_URL}'>{APP_MANATOOLS_URL}</a></li>"
        "</ul>"
    )
    runtime_info = (
        f"<h3>{_("Runtime")}</h3>"
        "<ul>"
        f"<li><b>python-manatools:</b> {_python_manatools_version()}</li>"
        "</ul>"
    )
    app.application_name = _(APP_DISPLAY_NAME)
    app.version = __version__
    app.license = APP_LICENSE
    app.description = _(APP_DESCRIPTION)
    app.authors = authors
    app.information = information + runtime_info
    app.logo = APP_ICON_PATH
    try:
        app.setApplicationIcon(APP_ICON_NAME)
    except Exception:
        logger.exception("Unable to set application icon by name %s", APP_ICON_NAME)


def main(argv=None):
    """Start the hostname control dialog and return an exit code."""
    if argv is None:
        argv = sys.argv[1:]
    early_locales_dir = _extract_locales_dir(argv)
    _configure_i18n(early_locales_dir or DEFAULT_LOCALE_DIR)

    parser = _create_args_parser(early_locales_dir or DEFAULT_LOCALE_DIR)
    parser.description = _(APP_CLI_DESCRIPTION)
    parser.add_argument("--logging", action="store_true", help=_("Enable application logging on the console."))
    parser.add_argument("--log-file", metavar="PATHNAME", help=_("Write log entries to PATHNAME instead of the console."))
    parser.add_argument("--debug", action="store_true", help=_("Enable debug logging output."))

    args = parser.parse_args(argv)
    if args.gtk:
        os.environ["MUI_BACKEND"] = "gtk"
    elif args.ncurses:
        os.environ["MUI_BACKEND"] = "ncurses"
    elif args.qt:
        os.environ["MUI_BACKEND"] = "qt"
    if args.locales_dir:
        _configure_i18n(args.locales_dir)

    from .dialog import HostnameDialog
    from .hostname_state import HostnameStatus

    _configure_logging(args)

    if args.version:
        print(f"{APP_NAME} {__version__}")
        return 0

    try:
        _configure_application_metadata()
        snapshot = HostnameStatus.load()
        logger.info("Loaded hostname snapshot from %s", snapshot.source)
        dialog = HostnameDialog(snapshot)
        dialog.run()
        return 0
    except Exception:
        logger.exception("Failed to start the hostname control dialog")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
