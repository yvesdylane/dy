from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from db.database import Base
from models.enums import Department


class CleaningGroup(Base):
    __tablename__ = "cleaning_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    department = Column(Enum(Department), nullable=False)
    turn_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    members = relationship(
        "CleaningGroupMember",
        back_populates="group",
        cascade="all, delete-orphan",
    )


class CleaningGroupMember(Base):
    __tablename__ = "cleaning_group_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(
        Integer,
        ForeignKey("cleaning_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    cycle_cleaned = Column(Boolean, default=False)

    group = relationship("CleaningGroup", back_populates="members")
    user = relationship("User")


class CleaningDuty(Base):
    __tablename__ = "cleaning_duties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(
        Integer,
        ForeignKey("cleaning_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    date = Column(Date, nullable=False)
    status = Column(String(20), default="pending")
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    group = relationship("CleaningGroup")
    completions = relationship(
        "CleaningCompletion",
        back_populates="duty",
        cascade="all, delete-orphan",
    )


class CleaningCompletion(Base):
    __tablename__ = "cleaning_completions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    duty_id = Column(
        Integer,
        ForeignKey("cleaning_duties.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    completed_at = Column(DateTime, default=datetime.utcnow)

    duty = relationship("CleaningDuty", back_populates="completions")
    user = relationship("User")
