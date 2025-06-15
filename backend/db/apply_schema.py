from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
from backend.core.settings import settings


if not settings.DATABASE_URL:
    raise ValueError("DATABASE_URL environment not set")

DATABASE_URL_STR = str(settings.DATABASE_URL)
if not DATABASE_URL_STR:
    raise ValueError("DATABASE_URL becomes empty string in apply_schema.py")


engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
