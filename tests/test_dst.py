from hw_timetable import ics_builder, models
from hw_timetable.util import parse_timezone


def make_activity():
    return models.Activity(
        CourseCode="ABC123",
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
        Weeks=[
            models.Week(WeekNumber=4, StartDate="2023-10-23"),
            models.Week(WeekNumber=5, StartDate="2023-10-30"),
        ],
        RunningWeeks=[],
        ScheduledDay=0,
        Locations=[models.Location(Building="B", Room="R")],
        InstructorAccounts=[],
        ActivityWeekLabel="Week",
    )


def test_dst_conversion():
    tz = parse_timezone("Europe/London")
    programme_info = {
        "AcademicYear": "2023/4",
        "CampusCode": "SCO",
        "Cohort": "1",
        "Semesters": ["S1"],
    }
    ics, _ = ics_builder.build_ics(programme_info, [make_activity()], [], tz=tz)
    assert "DTSTART:20231023T080000Z" in ics
    assert "DTSTART:20231030T090000Z" in ics
