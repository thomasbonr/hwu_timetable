import json
import shutil
import subprocess
import sys
from pathlib import Path

from hw_timetable import ics_builder


def test_offline_cli_execution():
    base = Path("out")
    if base.exists():
        shutil.rmtree(base)
    json_dir = base / "json"
    json_dir.mkdir(parents=True)
    (base / "ics").mkdir(parents=True)

    with (json_dir / "Student_programme-info.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "AcademicYear": "2023/4",
                "CampusCode": "SCO",
                "Cohort": "1",
                "Semesters": ["S1"],
            },
            f,
        )
    with (json_dir / "systemadmin_semesters.json").open("w", encoding="utf-8") as f:
        json.dump(
            [
                {
                    "Code": "S1",
                    "StartDate": "2023-09-04",
                    "EndDate": "2023-12-15",
                }
            ],
            f,
        )
    with (json_dir / "activity_activities.json").open("w", encoding="utf-8") as f:
        json.dump(
            [
                {
                    "CourseCode": "ABC",
                    "CourseName": "Course",
                    "ActivityName": "Lec",
                    "ActivityTypeDescription": "Lecture",
                    "Type": "Lecture",
                    "Group": None,
                    "Cohort": None,
                    "ProgrammeCodes": ["PC"],
                    "SemesterCode": "S1",
                    "StartTime": "09:00:00",
                    "EndTime": "10:00:00",
                    "Weeks": [{"WeekNumber": 1, "StartDate": "2023-09-04"}],
                    "RunningWeeks": [],
                    "ScheduledDay": 0,
                    "Locations": [{"Building": "B", "Room": "1"}],
                    "InstructorAccounts": [],
                    "ActivityWeekLabel": "Week",
                }
            ],
            f,
        )
    for name in [
        "activity_blocked-out-periods.json",
        "activity_ad-hoc.json",
    ]:
        with (json_dir / name).open("w", encoding="utf-8") as f:
            json.dump([], f)

    subprocess.run([sys.executable, "-m", "hw_timetable.cli", "--offline"], check=True)
    expected = Path("out/ics") / ics_builder.output_filename(
        {
            "AcademicYear": "2023/4",
            "CampusCode": "SCO",
            "Cohort": "1",
            "Semesters": ["S1"],
        }
    )
    assert expected.exists()
