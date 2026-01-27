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
    return dt.strftime("%Y%m%dT%H%M%SZ")
def _format_local(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S")
def _escape_text(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    escaped = normalized.replace("\\", "\\\\")
    escaped = escaped.replace("\n", "\\n")
    escaped = escaped.replace(",", "\\,")
    escaped = escaped.replace(";", "\\;")
    return escaped

# ---- Location parsing & normalization helpers ----
def _ws(s: str) -> str:
    return " ".join(str(s).split()) if s is not None else ""

def _norm_building(b: str) -> str:
    # Keep original casing but normalize whitespace
    return _ws(b)

def _norm_room(r: str) -> str:
    # Normalize whitespace and uppercase room codes like JW1
    return _ws(r).upper()

def _get_loc_field(loc: any, *names: str) -> str:
    for n in names:
        if hasattr(loc, n):
            v = getattr(loc, n, None)
        elif isinstance(loc, dict):
            v = loc.get(n)
        else:
            v = None
        if v:
            return str(v)
    return ""

def _build_location_string(act: any) -> str:
    building_order: List[str] = []
    building_rooms: Dict[str, List[str]] = {}
    extras: List[str] = []
    extras_seen: set[str] = set()
    for loc in getattr(act, "Locations", []) or []:
        building = _norm_building(
            _get_loc_field(
                loc,
                "Building",
                "BuildingName",
                "Site",
                "Campus",
                "LocationBuilding",
            )
        )
        room = _norm_room(
            _get_loc_field(
                loc,
                "Location",
                "Room",
                "RoomCode",
                "RoomName",
                "RoomNumber",
                "Space",
                "Code",
            )
        )
        full = _ws(
            _get_loc_field(
                loc,
                "DisplayName",
                "Description",
                "LocationDescription",
                "Name",
                "FullName",
            )
        )
        if building:
            if building not in building_rooms:
                building_rooms[building] = []
                building_order.append(building)
            if room and room not in building_rooms[building]:
                building_rooms[building].append(room)
        elif room:
            if room and room not in extras_seen:
                extras.append(room)
                extras_seen.add(room)
        elif full:
            if full and full not in extras_seen:
                extras.append(full)
                extras_seen.add(full)
    parts: List[str] = []
    seen_parts: set[str] = set()
    for building in building_order:
        rooms = building_rooms[building]
        if rooms:
            part = f"{building} - {', '.join(rooms)}"
        else:
            part = building
        if part and part not in seen_parts:
            parts.append(part)
            seen_parts.add(part)
    for extra in extras:
        if extra and extra not in seen_parts:
            parts.append(extra)
            seen_parts.add(extra)
    return " / ".join(parts)
# ---- End helpers ----

def _fold_line(line: str, limit: int = 75) -> List[str]:
    if len(line.encode("utf-8")) <= limit:
        return [line]
    folded: List[str] = []
    current_chars: List[str] = []
    current_bytes = 0
    for ch in line:
        ch_bytes = len(ch.encode("utf-8"))
        if current_bytes + ch_bytes > limit:
            if current_chars:
                folded.append("".join(current_chars))
            current_chars = [" "]
            current_bytes = 1
        current_chars.append(ch)
        current_bytes += ch_bytes
    if current_chars:
        folded.append("".join(current_chars))
    return folded
def _format_lines(lines: Iterable[str]) -> str:
    formatted: List[str] = []
    for line in lines:
        if not line:
            continue
        formatted.extend(_fold_line(line))
    return "\r\n".join(formatted) + "\r\n"
def build_events(
    activities: Iterable[Activity],
    *,
    tz: ZoneInfo,
    start: Optional[date] = None,
    end: Optional[date] = None,
    filter_courses: Optional[set[str]] = None,
    filter_types: Optional[set[str]] = None,
) -> List[dict]:
    groups: Dict[Tuple[str, ...], Dict[str, Any]] = {}
    for act in activities:
        if filter_courses and act.CourseCode not in filter_courses:
            continue
        act_type = act.ActivityTypeDescription or act.Type
        if filter_types and act_type not in filter_types:
            continue
        weeks = act.Weeks or act.RunningWeeks
        for week in weeks:
            start_date_str = (week.StartDate if hasattr(week, "StartDate") else week["StartDate"])
            occ_date = _parse_date(start_date_str) + timedelta(days=act.ScheduledDay)
            if act.StartDate and occ_date < _parse_date(act.StartDate):
                continue
            if act.EndDate and occ_date > _parse_date(act.EndDate):
                continue
            if start and occ_date < start:
                continue
            if end and occ_date > end:
                continue
            location = _build_location_string(act)
            instructors: List[str] = []
            for ins in act.InstructorAccounts:
                name = (ins.DisplayName if hasattr(ins, "DisplayName") else ins.get("DisplayName",""))
                if name:
                    instructors.append(name.strip())
            description_parts = [
                (f"Instructor(s): {', '.join([n for n in instructors if n])}" if instructors else ""),
                (f"Course: {act.CourseName}" if act.CourseName else ""),
                (f"Group: {act.Group}" if getattr(act, "Group", None) else ""),
                (f"Cohort: {act.Cohort}" if getattr(act, "Cohort", None) else ""),
                (f"Week: {act.ActivityWeekLabel}" if act.ActivityWeekLabel else ""),
                (f"Activity code: {act.ActivityName}" if act.ActivityName else ""),
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
                    "summary": " - ".join(
                        [
                            part
                            for part in (
                                act.CourseCode,
                                act.CourseName,
                                act_type,
                            )
                            if part
                        ]
                    ),
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
        events.extend(build_blocked_events(blocked_periods, tz=tz, start=start, end=end))
    now = datetime.now(timezone.utc)
    calendar_name = (
        _normalize_str(
            _pick_field(
                programme_info,
                (
                    "CalendarName",
                    "ProgrammeName",
                    "ProgrammeDescription",
                    "ProgrammeCode",
                ),
            )
        )
        or "HW Timetable"
    )
    academic_year = _extract_academic_year(programme_info)
    campus = _extract_component(
        programme_info,
        ("CampusCode", "Campus", "CampusName", "CampusDescription"),
        "campus",
    )
    cohort = _extract_component(
        programme_info,
        ("Cohort", "CohortCode", "ProgrammeCode", "ProgrammeName"),
        "cohort",
    )
    semester_label = _extract_semester_label(programme_info, activities)
    calendar_desc = " | ".join(
        [
            f"Academic year: {academic_year}",
            f"Campus: {campus}",
            f"Cohort: {cohort}",
            f"Semesters: {semester_label}",
        ]
    )
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//HW Timetable Exporter//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape_text(calendar_name)}",
        f"X-WR-CALDESC:{_escape_text(calendar_desc)}",
        "X-WR-TIMEZONE:Europe/London",
    ]
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
        lines.append(f"DTSTART;TZID=Europe/London:{_format_local(e['start'])}")
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
    ics = _format_lines(lines)
    return ics, events
def _pick_field(payload: dict, names: Tuple[str, ...]) -> Any:
    for name in names:
        if name in payload:
            value = payload[name]
            if value not in (None, "", []):
                return value
    return None


def _normalize_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return str(value)


def _extract_academic_year(programme_info: dict) -> str:
    year_value = _pick_field(
        programme_info,
        (
            "AcademicYear",
            "AcademicYearName",
            "AcademicYearDescription",
            "AcademicSession",
            "CurrentAcademicYear",
            "AcademicYearCode",
        ),
    )
    cleaned = _normalize_str(year_value)
    if cleaned:
        return cleaned.replace("/", "-")
    return "unknown"


def _extract_component(programme_info: dict, names: Tuple[str, ...], default: str) -> str:
    value = _normalize_str(_pick_field(programme_info, names))
    return value or default


def _coerce_semester_tokens(raw: Any) -> List[str]:
    tokens: List[str] = []
    if raw is None:
        return tokens
    if isinstance(raw, str):
        stripped = raw.strip()
        if stripped:
            tokens.append(stripped)
        return tokens
    if isinstance(raw, dict):
        for key in ("Code", "SemesterCode", "Name", "Description"):
            if raw.get(key):
                tokens.extend(_coerce_semester_tokens(raw[key]))
                break
        return tokens
    if isinstance(raw, (list, tuple, set)):
        for item in raw:
            tokens.extend(_coerce_semester_tokens(item))
        return tokens
    tokens.append(str(raw))
    return tokens


def _extract_semester_label(
    programme_info: dict,
    activities: Iterable[Activity] | None,
) -> str:
    semester_source = _pick_field(
        programme_info,
        (
            "Semesters",
            "SemesterCodes",
            "ProgrammeSemesters",
            "SemestersList",
            "Semester",
        ),
    )
    tokens = _coerce_semester_tokens(semester_source)
    if not tokens and activities is not None:
        codes = sorted(
            {
                getattr(act, "SemesterCode", None)
                for act in activities
                if getattr(act, "SemesterCode", None)
            }
        )
        tokens = [c for c in codes if c]
    return "-".join(tokens) if tokens else "None"


def output_filename(
    programme_info: dict,
    *,
    activities: Iterable[Activity] | None = None,
) -> str:
    year = _extract_academic_year(programme_info)
    campus = _extract_component(
        programme_info,
        ("CampusCode", "Campus", "CampusName", "CampusDescription"),
        "campus",
    )
    cohort = _extract_component(
        programme_info,
        ("Cohort", "CohortCode", "ProgrammeCode", "ProgrammeName"),
        "cohort",
    )
    sem = _extract_semester_label(programme_info, activities)
    return f"hw_timetable_{year}_{campus}_{cohort}_{sem}.ics"
