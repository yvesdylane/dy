from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from db.database import Base
from models.enums import Group


class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    group = Column(Enum(Group), nullable=False)

    __table_args__ = (
        UniqueConstraint("date", "group", name="uq_attendance_date_group"),
    )

    intern_attendances = relationship("InternAttendance", back_populates="attendance")


class InternAttendance(Base):
    __tablename__ = "intern_attendances"

    attendance_id = Column(Integer, ForeignKey("attendances.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    enter_at = Column(DateTime, nullable=False)
    left_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=True)

    attendance = relationship("Attendance", back_populates="intern_attendances")
    user = relationship("User", back_populates="attendances")


class AttendanceCode(Base):
    __tablename__ = "attendance_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(5), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
