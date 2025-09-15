"""ICS calendar builder."""

from __future__ import annotations

import hashlib
from datetime import date, datetime, time, timedelta, timezone
from typing import Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo

from .models import Activity, BlockedPeriod

DASHBOARD_URL = "https://timetableexplorer.hw.ac.uk/timetable-dashboard"


def _parse_date(s: str) -> date:
    return datetime.fromisoformat(s.replace('Z', '')).date()


def _parse_time(s: str) -> time:
    return datetime.strptime(s, "%H:%M:%S").time()


def _format(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _uid(activity: Activity, occ_date: date) -> str:
    base = (
        f"{activity.CourseCode}|{activity.ActivityName}|{occ_date}|{activity.StartTime}"
    )
    return hashlib.sha1(base.encode()).hexdigest()


def build_events(
    activities: Iterable[Activity],
    *,
    tz: ZoneInfo,
    start: Optional[date] = None,
    end: Optional[date] = None,
    filter_courses: Optional[set[str]] = None,
    filter_types: Optional[set[str]] = None,
) -> List[dict]:
    events: List[dict] = []
    seen_uids: set[str] = set()
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
            uid = _uid(act, occ_date)
            if uid in seen_uids:
                continue
            seen_uids.add(uid)
            start_dt = datetime.combine(occ_date, _parse_time(act.StartTime), tz)
            end_dt = datetime.combine(occ_date, _parse_time(act.EndTime), tz)
            start_utc = start_dt.astimezone(timezone.utc)
            end_utc = end_dt.astimezone(timezone.utc)
            location_parts = []
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
            instructors = []
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
            description = "\\n".join(filter(None, description_parts))
            events.append(
                {
                    "uid": uid,
                    "start": start_utc,
                    "end": end_utc,
                    "summary": f"{act.CourseCode} – {act_type}",
                    "location": location,
                    "description": description,
                    "categories": act_type,
                    "transp": "OPAQUE",
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
        start_utc = start_dt.astimezone(timezone.utc)
        end_utc = end_dt.astimezone(timezone.utc)
        summary = p.Description or "Blocked out period"
        uid = hashlib.sha1(f"{summary}|{occ_date}|{p.StartTime}".encode()).hexdigest()
        events.append(
            {
                "uid": uid,
                "start": start_utc,
                "end": end_utc,
                "summary": summary,
                "location": "",
                "description": summary,
                "categories": "Blocked",
                "transp": "TRANSPARENT",
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
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//HW Timetable Exporter//EN"]
    for e in events:
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{e['uid']}")
        lines.append(f"DTSTAMP:{_format(now)}")
        lines.append(f"SUMMARY:{e['summary']}")
        lines.append(f"DTSTART:{_format(e['start'])}")
        lines.append(f"DTEND:{_format(e['end'])}")
        if e["location"]:
            lines.append(f"LOCATION:{e['location']}")
        if e["description"]:
            lines.append(f"DESCRIPTION:{e['description']}")
        lines.append(f"CATEGORIES:{e['categories']}")
        lines.append(f"URL:{DASHBOARD_URL}")
        lines.append("STATUS:CONFIRMED")
        lines.append(f"TRANSP:{e['transp']}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    ics = "\r\n".join(lines) + "\r\n"
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
