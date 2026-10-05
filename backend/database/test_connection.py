from sqlalchemy import text
from connection import engine

with engine.connect() as connection:
    result = connection.execute(text("SELECT version();"))
    print(result.scalar())