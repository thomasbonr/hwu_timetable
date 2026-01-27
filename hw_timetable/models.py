from __future__ import annotations

from typing import List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class Week(BaseModel):
    model_config = ConfigDict(extra="ignore")

    WeekNumber: Optional[int] = None
    StartDate: str  # ISO date string


class Location(BaseModel):
    model_config = ConfigDict(extra="allow")

    Building: Optional[str] = None
    Room: Optional[str] = None
    # Add other location aliases if they appear in the API (e.g., RoomCode)
    # Pydantic can map these using Field(validation_alias=...) if needed.


class Instructor(BaseModel):
    model_config = ConfigDict(extra="allow")

    DisplayName: Optional[str] = None
    Email: Optional[str] = None


class Activity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    CourseCode: str
    CourseName: str
    ActivityName: Optional[str] = None
    ActivityTypeDescription: Optional[str] = None
    Type: Optional[str] = None
    Group: Optional[str] = None
    Cohort: Optional[str] = None
    ProgrammeCodes: List[str] = Field(default_factory=list)
    SemesterCode: Optional[str] = None
    StartTime: str
    EndTime: str

    Weeks: List[Week] = Field(default_factory=list)
    RunningWeeks: List[Week] = Field(default_factory=list)

    ScheduledDay: int = 0
    StartDate: Optional[str] = None
    EndDate: Optional[str] = None

    Locations: List[Location] = Field(default_factory=list)
    InstructorAccounts: List[Instructor] = Field(default_factory=list)

    ActivityWeekLabel: Optional[str] = ""

    @field_validator("Weeks", "RunningWeeks", mode="before")
    @classmethod
    def _coerce_week_lists(cls, value):
        # Normalize null/empty values and bitstring encodings.
        if value in (None, ""):
            return []
        if isinstance(value, str):
            return []
        return value


class BlockedPeriod(BaseModel):
    model_config = ConfigDict(extra="ignore")

    Description: Optional[str] = None
    StartDate: str
    EndDate: str
    StartTime: str
    EndTime: str
