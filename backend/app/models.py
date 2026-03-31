from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import uuid


Base = declarative_base()


def new_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id              = Column(String, primary_key=True, default=new_uuid)
    email           = Column(String, unique=True, nullable=False, index=True)
    username        = Column(String, unique=True, nullable=True)
    name            = Column(String)
    hashed_password = Column(String, nullable=True)  # null for Google-only users
    google_id       = Column(String, unique=True, nullable=True)
    role            = Column(String, default="advisor")  # advisor | admin | readonly
    created_at      = Column(DateTime, default=datetime.utcnow)


class Case(Base):
    __tablename__ = "cases"

    id         = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    advisor_id = Column(UUID(as_uuid=False), nullable=True)
    summary    = Column(Text, nullable=True)
    notes      = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship(
        "Message",
        back_populates="case",
        cascade="all, delete",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    case_id    = Column(UUID(as_uuid=False), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    role       = Column(String, nullable=False)  # "user" | "assistant"
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="messages")
