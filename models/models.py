import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from db.database import Base


class Gender(enum.Enum):
    male = "male"
    female = "female"


class Role(enum.Enum):
    intern = "intern"
    instructor = "instructor"
    admin = "admin"


class Department(enum.Enum):
    ISM = "ISM"
    SWE = "SWE"
    CGWD = "CGWD"
    EDM = "EDM"
    CSNW =  "CSNW"
    DBM = "DBM"
    CNWS = "CNWS"
    NS = "NS"


class Group(enum.Enum):
    A = "A"
    B = "B"


class ComplainType(enum.Enum):
    complaint = "complaint"
    advice = "advice"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    surname = Column(String(100), nullable=False)
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

    attendance_id = Column(
        Integer, ForeignKey("attendances.id"), primary_key=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    enter_at = Column(DateTime, nullable=False)
    left_at = Column(DateTime, nullable=True)

    attendance = relationship("Attendance", back_populates="intern_attendances")
    user = relationship("User", back_populates="attendances")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    supporting_doc = Column(String(500), nullable=True)
    file_id = Column(String(200), nullable=True)
    file_name = Column(String(200), nullable=True)
    department = Column(Enum(Department), nullable=False)
    submission_deadline = Column(DateTime, nullable=False)
    total_mark_on = Column(Integer, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", back_populates="created_tasks")
    submissions = relationship("TaskSubmission", back_populates="task")


class TaskSubmission(Base):
    __tablename__ = "task_submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    submitted_file = Column(String(500), nullable=False)
    file_id = Column(String(200), nullable=True)
    file_name = Column(String(200), nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    mark_obtained = Column(Numeric(5, 2), nullable=True)
    feedback = Column(Text, nullable=True)

    task = relationship("Task", back_populates="submissions")
    user = relationship("User", back_populates="task_submissions")


class Info(Base):
    __tablename__ = "infos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    file_url = Column(String(500), nullable=True)
    file_id = Column(String(200), nullable=True)
    file_name = Column(String(200), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", back_populates="infos")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    file_url = Column(String(500), nullable=True)
    file_id = Column(String(200), nullable=True)
    file_name = Column(String(200), nullable=True)
    department = Column(Enum(Department), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    uploader = relationship("User", back_populates="notes")


class UserComplain(Base):
    __tablename__ = "user_complains"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    complain_type = Column(Enum(ComplainType), nullable=False)
    department = Column(Enum(Department), nullable=False)
    group = Column(Enum(Group), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
