from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Integer, Text

from db.database import Base
from models.enums import ComplainType, Department, Group


class UserComplain(Base):
    __tablename__ = "user_complains"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    complain_type = Column(Enum(ComplainType), nullable=False)
    department = Column(Enum(Department), nullable=False)
    group = Column(Enum(Group), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
