# HW Timetable Exporter

Command-line utility that fetches Heriot-Watt University timetable data and
produces standards-compliant iCalendar (`.ics`) files that can be imported into
Nextcloud, Apple Calendar, Google Calendar, or any other CalDAV-capable
consumer.

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

- Python 3.11+ (matches the version targeted in `pyproject.toml`).
- Dependencies listed in `requirements.txt`:
  - `requests` for HTTPS API calls and optional token downloads.
  - `pydantic` for strict data validation.
  - `tzdata` to supply Olson timezone definitions on minimal distros such as
    Alpine.
- (Optional) `pytest`, `ruff`, and `black` for development—install via
  `pip install -e .[dev]` if desired.

## Installation

```bash
git clone https://github.com/<you>/hw_timetable.git
cd hw_timetable
python3 -m venv .venv && source .venv/bin/activate  # recommended
python3 -m pip install -r requirements.txt
```

## Authentication

Running the CLI requires an `Authorization: Bearer <token>` header. You can
provide the token via the `--token` flag, the `HW_TIMETABLE_ACCESS_TOKEN`
environment variable, or by reusing the cached value stored in
`~/.cache/hw_timetable/token.txt` (written automatically each time a token is
supplied).

### How to capture the bearer token via your browser

1. Sign in to the official HW timetable dashboard as usual.
2. Open your browser developer tools and switch to the "Network" tab.
3. Trigger any timetable action so that an API request appears (look for
  requests going to `https://timetableexplorer-api.hw.ac.uk/...`).
4. Click the API request, locate the **Request Headers** section, and copy the
  full value of the `Authorization` header—it should look like
  `Bearer eyJ0eXAiOiJKV1QiLCJhbGciOi...`.
5. Paste that value into a safe place (password manager, `.env` file, etc.) so
  the CLI can reuse it. You may keep the leading `Bearer ` prefix or remove it;
  the exporter strips it automatically before issuing requests. Tokens typically
  expire after a few hours, so repeat the steps whenever the API rejects a call.

### Supplying the token to the CLI

```bash
# Export the token for the current shell session
export HW_TIMETABLE_ACCESS_TOKEN="Bearer eyJ0eXAiOiJKV1QiLCJhbGciOi..."

# Download all JSON payloads (for offline runs) and generate the ICS preview
python3 -m hw_timetable.cli --dump-json --preview
```

Once JSON fixtures have been dumped locally, you can run with `--offline` to
avoid authenticating altogether:

```bash
python3 -m hw_timetable.cli --offline --preview
```

## Basic Usage

```bash
python3 -m hw_timetable.cli
```

By default, the tool writes a single `.ics` file into `out/ics/` using a file
name derived from your programme metadata. The file already contains
Nextcloud-friendly headers (`METHOD:PUBLISH`, `X-WR-CALNAME`, etc.), so you can
host it on any static server (including Alpine) and subscribe to it from a
CalDAV client.

### CLI options

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

### Publishing to Nextcloud (or any CalDAV client)

1. Generate the ICS file: `python3 -m hw_timetable.cli --preview`.
2. Copy the resulting file from `out/ics/` to your Alpine server (or keep it in
   place and serve the `out/ics` directory statically).
3. In Nextcloud Calendar, create a “New subscription from link” and paste the
   HTTPS URL of the hosted `.ics` file. The calendar metadata (`X-WR-CALNAME`,
   `X-WR-CALDESC`, `X-WR-TIMEZONE`) ensures the subscription displays a friendly
   name and correct timezone information automatically.

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
