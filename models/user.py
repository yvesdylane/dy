from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship

from db.database import Base
from models.enums import Department, Gender, Group, Role


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    surname = Column(String(100), nullable=False)
    email = Column(String(200), nullable=True)
    phone = Column(String(20), unique=True, nullable=False)
    telegram_id = Column(String(100), unique=True, nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    role = Column(Enum(Role), nullable=False)
    department = Column(Enum(Department), nullable=False)
    group = Column(Enum(Group), nullable=True)
    school = Column(String(200), nullable=False)
    dob = Column(Date, nullable=False)
    image = Column(String(500), nullable=True)
    quarter = Column(Integer, nullable=True)
    fees_paid = Column(Numeric(10, 2), default=0, nullable=True)
    total_fees = Column(Numeric(10, 2), default=40000, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    attendances = relationship("InternAttendance", back_populates="user")
    task_submissions = relationship("TaskSubmission", back_populates="user")
    created_codes = relationship("CreationCode", back_populates="creator")
    created_tasks = relationship("Task", back_populates="creator")
    infos = relationship("Info", back_populates="creator")
    notes = relationship("Note", back_populates="uploader")
    leave_requests = relationship(
        "LeaveRequest",
        foreign_keys="LeaveRequest.user_id",
        overlaps="reviewed_leaves",
    )
    reviewed_leaves = relationship(
        "LeaveRequest",
        foreign_keys="LeaveRequest.reviewed_by",
        overlaps="leave_requests",
    )
    face_embeddings = relationship(
        "FaceEmbedding", back_populates="user", cascade="all, delete-orphan"
    )


class CreationCode(Base):
    __tablename__ = "creation_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(200), unique=True, nullable=False)
    role = Column(Enum(Role), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", back_populates="created_codes")


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    embedding = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="face_embeddings")
