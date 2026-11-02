# manahost

<img src="manahost/resources/manahost.svg" alt="manahost" width="96" align="right" />

A small ManaTools dialog to inspect and edit the system hostname metadata
exposed by the `org.freedesktop.hostname1` D-Bus interface.

## Features

- reads hostname, static hostname, pretty hostname, icon name, chassis, and
  other hardware/system metadata
- exposes editable values through a `BaseDialog`\-based layout compatible with
  the python ManaTools backend abstraction library 
- logging
- provides a ManaTools `HelpDialog` with field explanations and tooltips on fields

## Requirements

`manahost` is a Python application built on top of the ManaTools UI framework.
For a normal runtime installation, the following requirements apply:

- Python: 3.9 or newer
- `python-manatools`: 0.99.3 or newer
- `dbus-python`
- `python-gettext`
- `PyYAML`
- a working D-Bus service exposing `org.freedesktop.hostname1` (typically
  `systemd-hostnamed` on systemd-based systems)

For packaging or source-based distribution builds, the project also expects the
usual build-time tooling for Python packages and gettext catalogs:

- `setuptools` / `wheel` (project uses `pyproject.toml`)
- `gettext` tools (`msgfmt`, `msgmerge`) so .po files can be compiled into .mo
  files before packaging

<br clear="right"/>

## Screenshots

### Qt backend
![Qt backend](<screenshots/ManaHost Qt.png> "Qt backend")

### Gtk backend
![Gtk backend](<screenshots/ManaHost Gtk.png> "Gtk backend")

### ncurses backend
![ncurses backend](<screenshots/ManaHost ncurses.png> "ncurses backend")

### web backend
![web backend](<screenshots/ManaHost web.png> "web backend")

## Usage

Run directly from the project directory:

```bash
python3 -m manahost --logging
```
Or use the wrapper script:

```bash
./bin/manahost --debug --log-file /tmp/manahost.log
```
Force a backend explicitly:

```bash
./bin/manahost --qt
./bin/manahost --gtk
./bin/manahost --ncurses
```
## Installation

```bash
python3 -m pip install .
```
After installation, the command becomes:

```bash
manahost --logging
```

Installed desktop integration files:
- `share/applications/manahost.desktop`
- `share/icons/hicolor/*/apps/manahost.png`
- `share/icons/hicolor/scalable/apps/manahost.svg`
## Notes

The app is D-Bus only: all reads and writes use `org.freedesktop.hostname1`
directly, and startup/save fail explicitly if D-Bus support is unavailable.
