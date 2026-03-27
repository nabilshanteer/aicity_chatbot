from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import uuid


Base = declarative_base()


def new_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id         = Column(String, primary_key=True, default=new_uuid)
    email      = Column(String, unique=True, nullable=False, index=True)
    name       = Column(String)
    google_id  = Column(String, unique=True)
    role       = Column(String, default="advisor")  # advisor | admin | readonly
    created_at = Column(DateTime, default=datetime.utcnow)

    chats = relationship("Chat", back_populates="user", cascade="all, delete")


class Chat(Base):
    __tablename__ = "chats"

    id         = Column(String, primary_key=True, default=new_uuid)
    user_id    = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title      = Column(String, default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)

    user     = relationship("User", back_populates="chats")
    messages = relationship(
        "Message",
        back_populates="chat",
        cascade="all, delete",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id         = Column(String, primary_key=True, default=new_uuid)
    chat_id    = Column(String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    role       = Column(String, nullable=False)  # "user" | "assistant"
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="messages")
