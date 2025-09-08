# HW Timetable Exporter

Command line utility to export Heriot-Watt University timetables to iCalendar.

## Installation

Clone the repository and install the dependencies:

```bash
pip install -r requirements.txt
```

## Authentication

Running the CLI requires an access token for the HW timetable API. When the
tool is executed it will use the Microsoft device login flow:

1. Run the command (see examples below).
2. Follow the instructions printed in the terminal – open the provided URL and
   enter the displayed code.
3. After signing in, the access token is cached under
   `~/.cache/hw_timetable/msal_cache.bin` for subsequent runs.

Alternatively, you can provide an existing token through the
`HW_TIMETABLE_ACCESS_TOKEN` environment variable. The `--offline` flag avoids
authentication entirely by using bundled JSON fixtures.

## Usage

```
python -m hw_timetable.cli --preview
python -m hw_timetable.cli --start 2024-01-08 --end 2024-05-10
python -m hw_timetable.cli --offline --dump-json
```

Generated calendar files are written to `out/ics`. See
`python -m hw_timetable.cli -h` for all available options.
