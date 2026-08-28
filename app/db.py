from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


class TriagedComment(Base):
    __tablename__ = "triaged_comments"

    ticket_id = Column(Integer, primary_key=True)
    comment_id = Column(Integer, primary_key=True)
    classification = Column(JSON, nullable=False)
    model_name = Column(String, nullable=False)
    prompt_version = Column(String, nullable=False)
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    zendesk_update_status = Column(String, nullable=False)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()