import datetime as dt
from pathlib import Path
from core.pipeline import process_full_exam

def test_pipeline():
    out_dir = Path("test_output_dir")
    videos = {
        "Prone": "does_not_exist.mp4",
        "Supine": "does_not_exist2.mp4",
        "Sitting": "does_not_exist3.mp4",
    }
    birthdate = dt.date.today() - dt.timedelta(days=100)
    
    print("Running process_full_exam with missing videos...")
    result = process_full_exam(videos, birthdate, out_dir)
    print("Success!")
    print(f"Age: {result['age_months']}")
    print(f"AIMS Score: {result['aims_score']}")
    print(f"Reports: {result['reports']}")

if __name__ == "__main__":
    test_pipeline()
