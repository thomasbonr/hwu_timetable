"""Data models for timetable entries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Week:
    WeekNumber: int
    StartDate: str  # ISO date string


@dataclass
class Location:
    Building: str
    Room: str


@dataclass
class Instructor:
    DisplayName: str
    Email: str | None = None


@dataclass
class Activity:
    CourseCode: str
    CourseName: str
    ActivityName: str
    ActivityTypeDescription: str
    Type: str
    Group: str | None
    Cohort: str | None
    ProgrammeCodes: List[str]
    SemesterCode: str
    StartTime: str
    EndTime: str
    Weeks: List[Week] = field(default_factory=list)
    RunningWeeks: List[Week] = field(default_factory=list)
    ScheduledDay: int = 0
    StartDate: Optional[str] = None
    EndDate: Optional[str] = None
    Locations: List[Location] = field(default_factory=list)
    InstructorAccounts: List[Instructor] = field(default_factory=list)
    ActivityWeekLabel: str = ""


@dataclass
class BlockedPeriod:
    Description: str
    StartDate: str
    EndDate: str
    StartTime: str
    EndTime: str
