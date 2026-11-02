# manahost

A small ManaTools dialog to inspect and edit the system hostname metadata
exposed by the `org.freedesktop.hostname1` D-Bus interface.

## Features

- reads hostname, static hostname, pretty hostname, icon name, chassis, and
  other hardware/system metadata
- exposes editable values through a `BaseDialog`\-based layout compatible with
  the python ManaTools backend abstraction library 
- logging
- provides a ManaTools `HelpDialog` with field explanations and tooltips on fields

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
## Notes

The app is D-Bus only: all reads and writes use `org.freedesktop.hostname1`
directly, and startup/save fail explicitly if D-Bus support is unavailable.

