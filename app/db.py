from typing import Iterator
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from db import make_engine, make_session

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('SQLALCHEMY_URL') or 'postgresql+psycopg2://postgres:postgres@localhost:5432/agentic_ai'

engine = make_engine(DATABASE_URL)
SessionLocal = make_session(engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
