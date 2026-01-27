from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from pathlib import Path
from typing import List

from . import api, ics_builder, models, util


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HW timetable exporter")
    parser.add_argument("--tz", default="Europe/London")
    parser.add_argument(
        "--include-blocked",
        dest="include_blocked",
        action="store_true",
        help="Include blocked out periods",
    )
    parser.add_argument(
        "--exclude-blocked",
        dest="include_blocked",
        action="store_false",
        help="Exclude blocked out periods",
    )
    parser.set_defaults(include_blocked=False)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--filter-course", action="append")
    parser.add_argument("--filter-type")
    parser.add_argument("--only-current-semester", action="store_true")
    parser.add_argument("--dump-json", action="store_true")
    parser.add_argument(
        "--offline", action="store_true", help="Use saved JSON fixtures"
    )
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--token",
        help="Explicit bearer token to call the HW timetable API",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> None:
    args = parse_args(argv)
    util.configure_logging(args.verbose)
    tz = util.parse_timezone(args.tz)
    start = date.fromisoformat(args.start) if args.start else None
    end = date.fromisoformat(args.end) if args.end else None
    filter_courses = set(args.filter_course) if args.filter_course else None
    filter_types = set(args.filter_type.split(",")) if args.filter_type else None

    token = None
    if not args.offline:
        from . import auth

        token = auth.acquire_token(explicit_token=args.token)

    client = api.APIClient(token, dump_json=args.dump_json, offline=args.offline)
    programme_info = client.get("/Student/programme-info")
    semesters = client.get("/systemadmin/semesters")
    activities_data = client.get("/activity/activities")
    blocked_data = client.get("/activity/blocked-out-periods")
    client.get("/activity/ad-hoc")  # fetched for completeness

    # --- REFACTOR START ---
    # Pydantic automatically handles validation and nested object creation.
    # We use model_validate (Pydantic v2) to parse the dictionary lists.
    activities = [models.Activity.model_validate(a) for a in activities_data]
    blocked_periods = [models.BlockedPeriod.model_validate(b) for b in blocked_data]
    # --- REFACTOR END ---

    if args.only_current_semester:
        today = util.today()
        current_sem = None
        for sem in semesters:
            # Safely get start/end dates
            s_date = sem.get("StartDate")
            e_date = sem.get("EndDate")
            if s_date and e_date:
                start_sem = date.fromisoformat(s_date)
                end_sem = date.fromisoformat(e_date)
                if start_sem <= today <= end_sem:
                    current_sem = sem.get("Code") or sem.get("SemesterCode")

        if current_sem:
            activities = [a for a in activities if a.SemesterCode == current_sem]

    ics, events = ics_builder.build_ics(
        programme_info,
        activities,
        blocked_periods,
        tz=tz,
        include_blocked=args.include_blocked,
        start=start,
        end=end,
        filter_courses=filter_courses,
        filter_types=filter_types,
    )

    out_dir = Path("out/ics")
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = ics_builder.output_filename(programme_info, activities=activities)
    # Write binary to avoid newline translation on Windows and preserve CRLF folding.
    (out_dir / filename).write_bytes(ics.encode("utf-8"))

    if args.preview:
        now = datetime.now(timezone.utc)
        upcoming = [e for e in events if e["start"] >= now]
        upcoming.sort(key=lambda e: e["start"])
        for e in upcoming[:10]:
            local_start = e["start"].astimezone(tz)
            local_end = e["end"].astimezone(tz)
            print(f"{local_start:%Y-%m-%d %H:%M} - {local_end:%H:%M} {e['summary']}")


if __name__ == "__main__":
    main()
