from hw_timetable import ics_builder, models
from hw_timetable.util import parse_timezone

PROGRAMME_INFO = {
    "AcademicYear": "2023/4",
    "CampusCode": "SCO",
    "Cohort": "1",
    "Semesters": ["S1"],
}


def make_activity(**overrides):
    base = {
        "CourseCode": "ABC",
        "CourseName": "Course",
        "ActivityName": "Lecture",
        "ActivityTypeDescription": "Lecture",
        "Type": "Lecture",
        "Group": None,
        "Cohort": None,
        "ProgrammeCodes": ["PC"],
        "SemesterCode": "S1",
        "StartTime": "09:00:00",
        "EndTime": "10:00:00",
        "Weeks": [models.Week(WeekNumber=1, StartDate="2023-09-04")],
        "RunningWeeks": [],
        "ScheduledDay": 0,
        "Locations": [],
        "InstructorAccounts": [],
        "ActivityWeekLabel": "Week",
    }
    base.update(overrides)
    return models.Activity(**base)


def extract_location_line(ics: str) -> str:
    for line in ics.splitlines():
        if line.startswith("LOCATION:"):
            return line
    return ""


def test_combines_rooms_for_building_and_escapes_commas():
    activity = make_activity(
        Locations=[
            {"Building": "James Watt Centre", "Location": "JW1"},
            {"Building": "James Watt Centre", "Room": "jw1"},
            {"Building": "James Watt Centre", "RoomName": "JW2"},
        ]
    )
    tz = parse_timezone("Europe/London")
    ics, _ = ics_builder.build_ics(PROGRAMME_INFO, [activity], [], tz=tz)
    assert extract_location_line(ics) == "LOCATION:James Watt Centre - JW1\\, JW2"


def test_multiple_buildings_listed_in_order():
    activity = make_activity(
        Locations=[
            {"Building": "David Brewster", "Room": "db1"},
            {"Building": "Grid", "Room": "G1"},
            {"Building": "David Brewster", "RoomCode": "DB2"},
        ]
    )
    tz = parse_timezone("Europe/London")
    ics, _ = ics_builder.build_ics(PROGRAMME_INFO, [activity], [], tz=tz)
    assert (
        extract_location_line(ics) == "LOCATION:David Brewster - DB1\\, DB2 / Grid - G1"
    )


def test_falls_back_to_display_name_when_no_building_or_room():
    activity = make_activity(Locations=[{"DisplayName": "Online"}])
    tz = parse_timezone("Europe/London")
    ics, _ = ics_builder.build_ics(PROGRAMME_INFO, [activity], [], tz=tz)
    assert extract_location_line(ics) == "LOCATION:Online"
