"""Engine/session setup, driven entirely by DATABASE_URL."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://ci_agent:change_me@localhost:5432/ci_agent"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    from db.models import Base

    Base.metadata.create_all(bind=engine)
