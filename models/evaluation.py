from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from db.database import Base
from models.enums import Department, Group


class DailyEvaluation(Base):
    __tablename__ = "daily_evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    scorer_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    punctuality = Column(Integer, nullable=True)
    professionalism = Column(Integer, nullable=True)
    dressing = Column(Integer, nullable=True)
    conduct = Column(Integer, nullable=True)
    teamwork = Column(Integer, nullable=True)
    participation = Column(Integer, nullable=True)
    leadership = Column(Integer, nullable=True)
    presentation = Column(Integer, nullable=True)
    communication = Column(Integer, nullable=True)

    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_evaluation_user_date"),
    )

    user = relationship("User", foreign_keys=[user_id])
    scorer = relationship("User", foreign_keys=[scorer_id])
