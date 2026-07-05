from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Integer, Text
from sqlalchemy.orm import relationship

from db.database import Base
from models.enums import ComplainType, Department, Group


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    complain_type = Column(Enum(ComplainType), nullable=False)
    department = Column(Enum(Department), nullable=False)
    group = Column(Enum(Group), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
