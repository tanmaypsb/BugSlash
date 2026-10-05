from connection import engine, Base
from models import Project, Scan, Finding 


Base.metadata.create_all(bind=engine)

print("BUGSLASH DATABASE TABLES CREATED SUCCESSFULLY")