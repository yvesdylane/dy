from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


engine = create_engine("mysql+asyncmy://user:pass@localhost/dy")
