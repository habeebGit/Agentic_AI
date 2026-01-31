from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine

Base = declarative_base()

def make_engine(dsn: str, **kwargs):
    """Create and return a SQLAlchemy engine.

    Example DSN: postgresql+psycopg2://user:pass@host:5432/dbname
    """
    return create_engine(dsn, **kwargs)

def make_session(engine):
    return sessionmaker(bind=engine)
