from sqlalchemy import Column, String, Text, DateTime, ForeignKey
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

    cases = relationship("Case", back_populates="user", cascade="all, delete")


class Case(Base):
    __tablename__ = "cases"

    id         = Column(String, primary_key=True, default=new_uuid)
    user_id    = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title      = Column(String, default="New Case")
    notes      = Column(Text, nullable=True)  # JSON array of confirmed note strings
    created_at = Column(DateTime, default=datetime.utcnow)

    user     = relationship("User", back_populates="cases")
    messages = relationship(
        "Message",
        back_populates="case",
        cascade="all, delete",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id         = Column(String, primary_key=True, default=new_uuid)
    case_id    = Column(String, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    role       = Column(String, nullable=False)  # "user" | "assistant"
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="messages")
