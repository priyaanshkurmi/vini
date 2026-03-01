import os
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DB_URL = os.getenv("DB_URL", "sqlite:///vini.db")

Base = declarative_base()
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)


class Memory(Base):
    __tablename__ = "memories"
    id       = Column(String, primary_key=True)
    content  = Column(Text)
    category = Column(String)   # 'fact' | 'emotion' | 'event' | 'summary'
    created  = Column(DateTime, default=datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    id       = Column(String, primary_key=True)
    role     = Column(String)  # 'user' | 'assistant'
    content  = Column(Text)
    created  = Column(DateTime, default=datetime.utcnow)
    session_id = Column(String, index=True)  # for grouping future multi-session support


# Create tables on import
Base.metadata.create_all(engine)
