from hw_timetable import ics_builder, models
from hw_timetable.util import parse_timezone


def test_duplicate_events_removed():
    act1 = models.Activity(
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
    act2 = act1
    tz = parse_timezone("Europe/London")
    programme_info = {
        "AcademicYear": "2023/4",
        "CampusCode": "SCO",
        "Cohort": "1",
        "Semesters": ["S1"],
    }
    ics, _ = ics_builder.build_ics(programme_info, [act1, act2], [], tz=tz)
    assert ics.count("BEGIN:VEVENT") == 1
