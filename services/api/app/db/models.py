from sqlalchemy import Column, String, Integer, Boolean, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class Camera(Base):
    __tablename__ = 'cameras'
    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    source_type = Column(String(20), nullable=False)  # 'webcam', 'file', 'rtsp'
    source_uri = Column(String, nullable=False)
    location = Column(String(100))
    zone = Column(String(100))
    priority = Column(Integer, default=1)
    enabled = Column(Boolean, default=True)
    status = Column(String(20), default='OFFLINE')
    last_frame_ts = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Event(Base):
    __tablename__ = 'events'
    event_id = Column(String(100), primary_key=True)
    type = Column(String(50), nullable=False, index=True)
    camera_id = Column(String(50), ForeignKey('cameras.id'), index=True)
    timestamp = Column(DateTime(timezone=True), primary_key=True, index=True)
    track_id = Column(String(50))
    confidence = Column(Float)
    severity = Column(String(20), default='INFO', index=True)
    status = Column(String(50), default='NEW')
    media_ref = Column(String)
    metadata_ = Column("metadata", JSON)  # metadata is a reserved word in SQLAlchemy Base
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Track(Base):
    __tablename__ = 'tracks'
    track_id = Column(String(50), primary_key=True)
    camera_id = Column(String(50), ForeignKey('cameras.id'))
    class_name = Column(String(50), nullable=False)
    first_seen = Column(DateTime(timezone=True), nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=False)
    trajectory = Column(JSON, nullable=False)

class WatchlistEntry(Base):
    __tablename__ = 'watchlist_entries'
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(20), nullable=False)  # 'FACE' or 'PLATE'
    label = Column(String(100), nullable=False)
    reference = Column(String)
    enabled = Column(Boolean, default=True)
    threshold = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Fence(Base):
    __tablename__ = 'fences'
    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(String(50), ForeignKey('cameras.id', ondelete='CASCADE'))
    name = Column(String(100))
    polygon = Column(JSON, nullable=False)
    direction = Column(String(20), default='BOTH')
    debounce_frames = Column(Integer, default=3)
    enabled = Column(Boolean, default=True)

class PlateRead(Base):
    __tablename__ = 'plate_reads'
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(100)) # Not setting a strict FK to allow partial logs, but normally FK to events
    plate_text = Column(String(50), nullable=False)
    ocr_confidence = Column(Float)
    format_valid = Column(Boolean, default=False)
    watchlist_hit = Column(Boolean, default=False)

class CameraHealth(Base):
    __tablename__ = 'camera_health'
    camera_id = Column(String(50), ForeignKey('cameras.id', ondelete='CASCADE'), primary_key=True)
    last_frame_ts = Column(DateTime(timezone=True))
    status = Column(String(20))
    fps = Column(Float)
    error_count = Column(Integer, default=0)

class AuditLog(Base):
    __tablename__ = 'audit_log'
    id = Column(Integer, primary_key=True, autoincrement=True)
    actor = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(String(100))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    metadata_ = Column("metadata", JSON)
