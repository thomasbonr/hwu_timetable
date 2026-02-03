# Heriot-Watt Timetable Exporter

Command-line utility that fetches Heriot-Watt University timetable data and
produces standards-compliant iCalendar (`.ics`) files that can be imported into Apple Calendar, Google Calendar, or any other CalDAV-capable
consumer.

[![Support this project](https://img.shields.io/badge/Support-PayPal-blue?logo=paypal)](https://paypal.me/ssthlgrkfdnlx)

## Highlights

- Generates compact weekly-recurring events with proper EXDATE handling.
- Emits `X-WR-*` metadata and CRLF line endings for maximum client
  compatibility (tested with Nextcloud and Alpine-based static hosting).
- Supports filtering by course, activity type, semester window, and optional
  blocked-period inclusion.
- Offers preview mode to quickly inspect the next few sessions in the terminal.
- Includes an offline workflow that reuses saved JSON payloads so credentials
  are only needed once.

## Requirements

- Python 3.11+.
- Dependencies listed in `requirements.txt`:
  - `requests` for HTTPS API calls and optional token downloads.
  - `pydantic` for strict data validation.
  - `tzdata` to supply Olson timezone definitions.
- (Optional) `pytest`, `ruff`, and `black` for development—install via
  `pip install -e .[dev]` if desired.

## Installation

```bash
git clone https://github.com/thomasbonr/hw_timetable.git
cd hw_timetable
python3 -m venv .venv && source .venv/bin/activate  # recommended
python3 -m pip install -r requirements.txt
```

## Authentication

Running the CLI requires an `Authorization: Bearer <token>` header. You can
provide the token via the `--token` flag, the `HW_TIMETABLE_ACCESS_TOKEN`
environment variable, a .env file, or by reusing the cached value stored in
`~/.cache/hw_timetable/token.txt` (written automatically each time a token is
supplied).

### How to capture the bearer token via your browser

1. Sign in to the official HW timetable dashboard as usual ([https://timetableexplorer.hw.ac.uk/timetable-dashboard](https://timetableexplorer.hw.ac.uk/timetable-dashboard)).
2. Open your browser developer tools and switch to the "Network" tab.
3. Ensure the persistant logs are enabled, and refresh the page (look for
  requests going to `https://timetableexplorer-api.hw.ac.uk/...`).
4. Click the API request, locate the **Request Headers** section, and copy the
  full value of the `Authorization` header—it should look like
  `Bearer eyJ0eXAiOiJKV1QiLCJhbGciOi...`.
5. Paste that value into a safe place, `.env` file, etc.) so
  the CLI can reuse it. You may keep the leading `Bearer ` prefix or remove it;
  Tokens expire after a ~1 hours, so repeat the steps whenever the API rejects a call.

<img width="2475" height="856" alt="Screenshot 2026-01-27 103544" src="https://github.com/user-attachments/assets/a7a57f0d-13aa-4296-a6ac-4162908d0ca1" />

### Supplying the token to the CLI (Recommended way)

```bash
# Export the token for the current shell session (Bash/macOS/Linux/WSL)
export HW_TIMETABLE_ACCESS_TOKEN="Bearer eyJ0eXAiOiJKV1QiLCJhbGciOi..."

# Download
python3 -m hw_timetable.cli
```

Windows users can set the environment variable with either PowerShell or
Command Prompt before running the CLI:

```powershell
# PowerShell
$env:HW_TIMETABLE_ACCESS_TOKEN = "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOi..."
python3 -m hw_timetable.cli
```

```bat
REM Command Prompt (cmd.exe)
set HW_TIMETABLE_ACCESS_TOKEN=Bearer eyJ0eXAiOiJKV1QiLCJhbGciOi...
python3 -m hw_timetable.cli
```

## Basic Usage

```bash
python3 -m hw_timetable.cli
```

By default, the tool writes a single `.ics` file into `out/ics/` using a file
name derived from your programme metadata.

### CLI options (Optional)

| Option | Description |
| --- | --- |
| `--tz Europe/London` | Override the timezone used for DTSTART/DTEND output. |
| `--include-blocked` / `--exclude-blocked` | Toggle inclusion of blocked periods (default: excluded). |
| `--start YYYY-MM-DD` / `--end YYYY-MM-DD` | Restrict events to a date range (inclusive). |
| `--filter-course CODE` | Append one or more course codes to include (repeat flag). |
| `--filter-type LEC,LAB` | Include only activities whose types match the comma-separated list. |
| `--only-current-semester` | Automatically detect the current semester window and drop the rest. |
| `--dump-json` | Save raw API responses under `out/json/` for auditing/offline use. |
| `--offline` | Read previously dumped JSON fixtures instead of calling the API. |
| `--preview` | Print the next 10 upcoming sessions to stdout after writing the ICS. |
| `--verbose` | Enable debug logging for HTTP retries and filtering decisions. |
| `--token` | Inline bearer token for protected API calls (overrides env/cache). |

All options can be combined. For example, to fetch Semester 2 labs only, dump
the raw payloads, and preview the next lectures:

```bash
python3 -m hw_timetable.cli \
  --filter-type Lab \
  --only-current-semester \
  --include-blocked \
  --dump-json \
  --preview
```

### Offline workflow

1. Run with valid credentials once while passing `--dump-json` to cache every
   endpoint: `python3 -m hw_timetable.cli --dump-json`.
2. Subsequent executions can use `--offline` (optionally together with
   `--dump-json` to refresh the cache) and therefore run without any network or
   authentication requirements: `python3 -m hw_timetable.cli --offline --preview`.


## Development

Format, lint, and test before opening a PR:

```bash
python3 -m pip install -e .[dev]
ruff check
black .
python3 -m pytest
```

The test suite exercises the ICS builder, timezone handling, and offline CLI
paths, so it is a good way to verify compatibility after making changes.
