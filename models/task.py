from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from db.database import Base
from models.enums import Department


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    supporting_doc = Column(String(500), nullable=True)
    file_id = Column(String(200), nullable=True)
    file_name = Column(String(200), nullable=True)
    department = Column(Enum(Department))
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
    submitted_file = Column(String(500), nullable=True)
    file_id = Column(String(200), nullable=True)
    file_name = Column(String(200), nullable=True)
    submitted_url = Column(String(1000), nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    mark_obtained = Column(Numeric(5, 2), nullable=True)
    feedback = Column(Text, nullable=True)

    task = relationship("Task", back_populates="submissions")
    user = relationship("User", back_populates="task_submissions")
