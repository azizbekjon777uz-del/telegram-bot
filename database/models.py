# database/models.py
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, BigInteger, ForeignKey
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Button(Base):
    __tablename__ = "buttons"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    emoji = Column(String(10), default="")
    parent_id = Column(Integer, ForeignKey("buttons.id"), nullable=True)
    content_type = Column(String(20), default="text")
    content_text = Column(Text, nullable=True)
    content_file_id = Column(String(200), nullable=True)
    order_num = Column(Integer, default=0)
    cols = Column(Integer, default=2)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    is_blocked = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=datetime.now)
    last_active = Column(DateTime, default=datetime.now)

class BroadcastLog(Base):
    __tablename__ = "broadcast_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_text = Column(Text, nullable=False)
    photo_file_id = Column(String(200), nullable=True)
    total_users = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    sent_at = Column(DateTime, default=datetime.now)

class Channel(Base):
    """Majburiy obuna kanallari"""
    __tablename__ = "channels"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(String(100), nullable=False)   # @username yoki -100xxxxxxxx
    channel_name = Column(String(200), nullable=False)
    channel_link = Column(String(300), nullable=True)  # https://t.me/...
    is_active = Column(Boolean, default=True)
    added_at = Column(DateTime, default=datetime.now)

class Admin(Base):
    """Qo'shimcha adminlar"""
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    added_at = Column(DateTime, default=datetime.now)

