"""ICS calendar builder."""

from __future__ import annotations

import hashlib
from datetime import date, datetime, time, timedelta, timezone
from typing import Iterable, List, Optional, Tuple, Dict, Any
from zoneinfo import ZoneInfo

from .models import Activity, BlockedPeriod

DASHBOARD_URL = "https://timetableexplorer.hw.ac.uk/timetable-dashboard"


def _parse_date(s: str) -> date:
    return datetime.fromisoformat(s.replace('Z', '')).date()


def _parse_time(s: str) -> time:
    return datetime.strptime(s, "%H:%M:%S").time()


def _format(dt: datetime) -> str:
    """Format a datetime in UTC with trailing Z."""
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _format_local(dt: datetime) -> str:
    """Format a datetime in local time without timezone suffix."""
    return dt.strftime("%Y%m%dT%H%M%S")


def _escape_text(value: str) -> str:
    """Escape text for RFC5545 TEXT value."""

    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    escaped = normalized.replace("\\", "\\\\")
    escaped = escaped.replace("\n", "\\n")
    escaped = escaped.replace(",", "\\,")
    escaped = escaped.replace(";", "\\;")
    return escaped


def _fold_line(line: str, limit: int = 75) -> List[str]:
    """Fold a line according to RFC5545 (75 octets)."""

    if len(line.encode("utf-8")) <= limit:
        return [line]

    folded: List[str] = []
    current_chars: List[str] = []
    current_bytes = 0

    for ch in line:
        ch_bytes = len(ch.encode("utf-8"))
        if current_bytes + ch_bytes > limit:
            folded.append("".join(current_chars))
            current_chars = [" "]
            current_bytes = 1
        current_chars.append(ch)
        current_bytes += ch_bytes

    folded.append("".join(current_chars))
    return folded

def build_events(
    activities: Iterable[Activity],
    *,
    tz: ZoneInfo,
    start: Optional[date] = None,
    end: Optional[date] = None,
    filter_courses: Optional[set[str]] = None,
    filter_types: Optional[set[str]] = None,
) -> List[dict]:
    """Build VEVENT structures collapsed by weekly recurrence."""

    groups: Dict[Tuple[str, ...], Dict[str, Any]] = {}

    for act in activities:
        if filter_courses and act.CourseCode not in filter_courses:
            continue
        act_type = act.ActivityTypeDescription or act.Type
        if filter_types and act_type not in filter_types:
            continue

        weeks = act.Weeks or act.RunningWeeks
        for week in weeks:
            start_date_str = (
                week.StartDate if hasattr(week, "StartDate") else week["StartDate"]
            )
            occ_date = _parse_date(start_date_str) + timedelta(days=act.ScheduledDay)

            if act.StartDate and occ_date < _parse_date(act.StartDate):
                continue
            if act.EndDate and occ_date > _parse_date(act.EndDate):
                continue
            if start and occ_date < start:
                continue
            if end and occ_date > end:
                continue

            location_parts: List[str] = []
            for loc in act.Locations:
                building = (
                    loc.Building
                    if hasattr(loc, "Building")
                    else loc.get("Building", "")
                )
                room = loc.Room if hasattr(loc, "Room") else loc.get("Room", "")
                part = f"{building} {room}".strip()
                if part:
                    location_parts.append(part)
            location = "/".join(location_parts)

            instructors: List[str] = []
            for ins in act.InstructorAccounts:
                name = (
                    ins.DisplayName
                    if hasattr(ins, "DisplayName")
                    else ins.get("DisplayName", "")
                )
                email = ins.Email if hasattr(ins, "Email") else ins.get("Email")
                instructors.append(f"{name} {email}".strip())

            description_parts = [
                act.CourseName,
                act.ActivityName,
                act.Group or "",
                act.Cohort or "",
                ",".join(act.ProgrammeCodes),
                act.SemesterCode,
                *instructors,
                act.ActivityWeekLabel,
            ]
            description = "\n".join(filter(None, description_parts))

            key = (
                act.CourseCode,
                act.ActivityName,
                act_type,
                location,
                str(act.ScheduledDay),
                act.StartTime,
                act.EndTime,
                act.ActivityWeekLabel,
            )

            group = groups.setdefault(
                key,
                {
                    "summary": f"{act.CourseCode} – {act_type or ''}",
                    "location": location,
                    "description": description,
                    "categories": act_type or "",
                    "transp": "OPAQUE",
                    "dates": [],
                    "start_time": act.StartTime,
                    "end_time": act.EndTime,
                    "course_code": act.CourseCode,
                    "activity_name": act.ActivityName,
                },
            )
            group["dates"].append(occ_date)

    events: List[dict] = []
    for group in groups.values():
        dates = sorted(group["dates"])
        start_time = _parse_time(group["start_time"])
        end_time = _parse_time(group["end_time"])
        first_date = dates[0]
        last_date = dates[-1]

        start_dt = datetime.combine(first_date, start_time, tz)
        end_dt = datetime.combine(first_date, end_time, tz)

        # Determine missing weeks for EXDATE
        exdates: List[datetime] = []
        cur = first_date
        seen = set(dates)
        while cur <= last_date:
            if cur not in seen:
                exdates.append(datetime.combine(cur, start_time, tz))
            cur += timedelta(days=7)

        last_start_utc = datetime.combine(last_date, start_time, tz).astimezone(timezone.utc)
        rrule = f"FREQ=WEEKLY;WKST=MO;UNTIL={_format(last_start_utc)}"

        uid_base = f"{group['course_code']}|{group['activity_name']}|{first_date}|{group['start_time']}|{group['location']}"
        uid = hashlib.sha1(uid_base.encode()).hexdigest()

        events.append(
            {
                "uid": uid,
                "summary": group["summary"],
                "location": group["location"],
                "description": group["description"],
                "categories": group["categories"],
                "transp": group["transp"],
                "start": start_dt,
                "end": end_dt,
                "rrule": rrule,
                "exdates": exdates,
            }
        )

    return events


def build_blocked_events(
    periods: Iterable[BlockedPeriod],
    *,
    tz: ZoneInfo,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> List[dict]:
    events: List[dict] = []
    for p in periods:
        occ_date = _parse_date(p.StartDate)
        if start and occ_date < start:
            continue
        if end and occ_date > end:
            continue
        start_dt = datetime.combine(occ_date, _parse_time(p.StartTime), tz)
        end_dt = datetime.combine(occ_date, _parse_time(p.EndTime), tz)
        summary = p.Description or "Blocked out period"
        uid = hashlib.sha1(f"{summary}|{occ_date}|{p.StartTime}".encode()).hexdigest()
        events.append(
            {
                "uid": uid,
                "start": start_dt,
                "end": end_dt,
                "summary": summary,
                "location": "",
                "description": summary,
                "categories": "Blocked",
                "transp": "TRANSPARENT",
                "rrule": None,
                "exdates": [],
            }
        )
    return events


def build_ics(
    programme_info: dict,
    activities: Iterable[Activity],
    blocked_periods: Iterable[BlockedPeriod],
    *,
    tz: ZoneInfo,
    include_blocked: bool = False,
    start: Optional[date] = None,
    end: Optional[date] = None,
    filter_courses: Optional[set[str]] = None,
    filter_types: Optional[set[str]] = None,
) -> Tuple[str, List[dict]]:
    events = build_events(
        activities,
        tz=tz,
        start=start,
        end=end,
        filter_courses=filter_courses,
        filter_types=filter_types,
    )
    if include_blocked:
        events.extend(
            build_blocked_events(blocked_periods, tz=tz, start=start, end=end)
        )

    now = datetime.now(timezone.utc)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//HW Timetable Exporter//EN",
    ]

    # Timezone definition for Europe/London
    lines.extend(
        [
            "BEGIN:VTIMEZONE",
            "TZID:Europe/London",
            "X-LIC-LOCATION:Europe/London",
            "BEGIN:DAYLIGHT",
            "TZOFFSETFROM:+0000",
            "TZOFFSETTO:+0100",
            "TZNAME:BST",
            "DTSTART:19700329T010000",
            "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU",
            "END:DAYLIGHT",
            "BEGIN:STANDARD",
            "TZOFFSETFROM:+0100",
            "TZOFFSETTO:+0000",
            "TZNAME:GMT",
            "DTSTART:19701025T020000",
            "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU",
            "END:STANDARD",
            "END:VTIMEZONE",
        ]
    )

    for e in events:
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{e['uid']}")
        lines.append(f"DTSTAMP:{_format(now)}")
        lines.append(f"SUMMARY:{_escape_text(e['summary'])}")
        lines.append(
            f"DTSTART;TZID=Europe/London:{_format_local(e['start'])}"
        )
        lines.append(f"DTEND;TZID=Europe/London:{_format_local(e['end'])}")
        if e.get("rrule"):
            lines.append(f"RRULE:{e['rrule']}")
        if e.get("exdates"):
            exdate_str = ",".join(_format_local(d) for d in e["exdates"])
            lines.append(f"EXDATE;TZID=Europe/London:{exdate_str}")
        if e["location"]:
            lines.append(f"LOCATION:{_escape_text(e['location'])}")
        if e["description"]:
            lines.append(f"DESCRIPTION:{_escape_text(e['description'])}")
        if e["categories"]:
            lines.append(f"CATEGORIES:{_escape_text(e['categories'])}")
        lines.append(f"URL:{DASHBOARD_URL}")
        lines.append("STATUS:CONFIRMED")
        lines.append(f"TRANSP:{e['transp']}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    folded_lines: List[str] = []
    for line in lines:
        folded_lines.extend(_fold_line(line))
    ics = "\r\n".join(folded_lines) + "\r\n"
    return ics, events


def output_filename(programme_info: dict) -> str:
    year = programme_info.get("AcademicYear", "unknown").replace("/", "-")
    campus = programme_info.get("CampusCode", "campus")
    cohort = programme_info.get("Cohort", "cohort")
    semesters = programme_info.get("Semesters")
    if isinstance(semesters, list):
        sem = "-".join(semesters)
    else:
        sem = str(semesters)
    return f"hw_timetable_{year}_{campus}_{cohort}_{sem}.ics"
