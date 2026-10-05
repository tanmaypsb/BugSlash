from connection import SessionLocal
from repository import save_scan


results = [
    {
        "findings": []
    }
]


db = SessionLocal()

try:
    scan = save_scan(
        db,
        "test_project.zip",
        results
    )

    print("Scan saved successfully.")
    print("Scan ID:", scan.id)

finally:
    db.close()