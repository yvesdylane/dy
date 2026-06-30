from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from db.database import Base
from models.enums import LeaveStatus


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.pending)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship(
        "User", foreign_keys=[user_id], overlaps="leave_requests"
    )
    reviewer = relationship(
        "User", foreign_keys=[reviewed_by], overlaps="reviewed_leaves"
    )
