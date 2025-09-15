from hw_timetable import ics_builder, models
from hw_timetable.util import parse_timezone


def test_weeks_preferred_over_runningweeks():
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
        Weeks=[
            models.Week(WeekNumber=5, StartDate="2023-10-02"),
            models.Week(WeekNumber=7, StartDate="2023-10-16"),
        ],
        RunningWeeks=[
            models.Week(WeekNumber=5, StartDate="2023-10-02"),
            models.Week(WeekNumber=6, StartDate="2023-10-09"),
            models.Week(WeekNumber=7, StartDate="2023-10-16"),
        ],
        ScheduledDay=0,
        Locations=[],
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
    assert "DTSTART;TZID=Europe/London:20231002T090000" in ics
    assert "EXDATE;TZID=Europe/London:20231009T090000" in ics
