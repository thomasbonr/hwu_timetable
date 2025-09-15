from hw_timetable import ics_builder, models
from hw_timetable.util import parse_timezone


def test_ics_structure():
    activity = models.Activity(
        CourseCode="ABC",
        CourseName="C",
        ActivityName="Lec",
        ActivityTypeDescription="Lecture",
        Type="Lecture",
        Group=None,
        Cohort=None,
        ProgrammeCodes=["PC"],
        SemesterCode="S1",
        StartTime="09:00:00",
        EndTime="10:00:00",
        Weeks=[models.Week(WeekNumber=1, StartDate="2023-09-04")],
        RunningWeeks=[],
        ScheduledDay=0,
        Locations=[models.Location(Building="B", Room="1")],
        InstructorAccounts=[],
        ActivityWeekLabel="Week",
    )
    tz = parse_timezone("Europe/London")
    programme_info = {
        "AcademicYear": "2023/4",
        "CampusCode": "SCO",
        "Cohort": "1",
        "Semesters": ["S1"],
    }
    ics, _ = ics_builder.build_ics(programme_info, [activity], [], tz=tz)
    assert "BEGIN:VCALENDAR" in ics
    assert "VERSION:2.0" in ics
    assert "PRODID:-//HW Timetable Exporter//EN" in ics
    assert ics.count("BEGIN:VEVENT") >= 1


def _build_single_activity(**overrides):
    base_activity = dict(
        CourseCode="ABC",
        CourseName="Course",
        ActivityName="Lecture",
        ActivityTypeDescription="Lecture",
        Type="Lecture",
        Group=None,
        Cohort=None,
        ProgrammeCodes=["PC"],
        SemesterCode="S1",
        StartTime="09:00:00",
        EndTime="10:00:00",
        Weeks=[models.Week(WeekNumber=1, StartDate="2023-09-04")],
        RunningWeeks=[],
        ScheduledDay=0,
        Locations=[models.Location(Building="B", Room="1")],
        InstructorAccounts=[],
        ActivityWeekLabel="Week",
    )
    base_activity.update(overrides)
    return models.Activity(**base_activity)


def _build_ics_with_activity(activity: models.Activity) -> str:
    tz = parse_timezone("Europe/London")
    programme_info = {
        "AcademicYear": "2023/4",
        "CampusCode": "SCO",
        "Cohort": "1",
        "Semesters": ["S1"],
    }
    ics, _ = ics_builder.build_ics(programme_info, [activity], [], tz=tz)
    return ics


def test_ics_uses_crlf_and_escapes_text():
    activity = _build_single_activity(
        CourseName="Course,Name",
        ActivityName="Lecture;Intro",
        Group="Group\\One",
        Cohort="Cohort",
    )

    ics = _build_ics_with_activity(activity)

    # All line endings must use CRLF
    assert "\n" not in ics.replace("\r\n", "")

    lines = ics.split("\r\n")
    desc_parts = []
    collecting = False
    for line in lines:
        if line.startswith("DESCRIPTION:"):
            desc_parts.append(line[len("DESCRIPTION:"):])
            collecting = True
        elif collecting and line.startswith(" "):
            desc_parts.append(line[1:])
        elif collecting:
            break
    description_value = "".join(desc_parts)

    assert "Course\\,Name" in description_value
    assert "Lecture\\;Intro" in description_value
    assert "Group\\\\One" in description_value
    assert "Week" in description_value
    assert "\\n" in description_value


def test_long_summary_is_folded():
    activity = _build_single_activity(CourseCode="X" * 90)
    ics = _build_ics_with_activity(activity)
    lines = ics.split("\r\n")

    summary_index = next(i for i, line in enumerate(lines) if line.startswith("SUMMARY:"))
    assert len(lines[summary_index].encode("utf-8")) <= 75
    assert lines[summary_index + 1].startswith(" ")
