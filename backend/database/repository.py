# THIS IS RESPONSIBLE FOR SAVING SCAN RESULTS TO POSTGRESQL


#importing the three tables from models
from database.models import Project, Scan, Finding 

def save_scan(db, project_name, results):
    #Creating Project

    project = Project(
        name=project_name,
    )

    db.add(project)
    db.flush()

    #creating scan for scanning purpose

    scan = Scan(
        project_id=project.id,
        status="completed",
        files_analyzed=len(results)
    )

    db.add(scan)
    db.flush()

    # Save findings
    for result in results:
        for finding in result["findings"]:

            db_finding = Finding(
                scan_id=scan.id,
                language=finding.language,
                file=finding.file,
                line=finding.line,
                column=finding.column,
                category=finding.category,
                severity=finding.severity,
                message=finding.message,
                analyzer=finding.analyzer,
                confidence=finding.confidence,
                verification_status=None
            )

            db.add(db_finding)

    db.commit()

    return scan.id

# when the analyzer returns example.py -> F841 or example.js -> no_unused_vars
# then this function created Scan#1 inside which are (finding#1, finding#2 etc)

# flush() ---> sends the INSERT to PostgreSql without permanently commiting the 
# transaction yet so we do it before db.commit() so that when the flush return project.id
# and scan.id we can use those id's for relationships

#postgresql --> all scans --> newest first
def get_scans(db):
    return (
        db.query(Scan)
        .order_by(Scan.created_at.desc())
        .all()
    )

#postgresql --> scan #7 --> its associated findings
def get_scan(db, scan_id):
    return (
        db.query(Scan)
        .filter(Scan.id == scan_id)
        .first()
    )

# Instead of returning the SQLAlchemy object directly, we're converting it into a normal Python dictionary while the database session is still open.
# That avoids the DetachedInstanceError problem we encountered earlier.
def get_scan_details(db, scan_id):
    scan = (
        db.query(Scan)
        .filter(Scan.id == scan_id)
        .first()
    )

    if scan is None:
        return None

    return {
        "id": scan.id,
        "project_id": scan.project_id,
        "status": scan.status,
        "files_analyzed": scan.files_analyzed,
        "created_at": scan.created_at,
        "findings": [
            {
                "id": finding.id,
                "language": finding.language,
                "file": finding.file,
                "line": finding.line,
                "column": finding.column,
                "category": finding.category,
                "severity": finding.severity,
                "message": finding.message,
                "analyzer": finding.analyzer,
                "confidence": finding.confidence,
                "verification_status": finding.verification_status,
            }
            for finding in scan.findings
        ],
    }