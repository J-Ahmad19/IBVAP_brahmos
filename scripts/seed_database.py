import os
import sys
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the api directory to the path so we can import the models
sys.path.append(os.path.join(os.path.dirname(__file__), '../services/api'))

from app.db.models import Base, Camera, Fence, Event, WatchlistEntry, CameraHealth

def get_engine():
    db_url = os.environ.get("DATABASE_URL", "postgresql+psycopg2://ibvap:ibvap_secret@localhost:5432/ibvap_db")
    if "asyncpg" in db_url:
        db_url = db_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    return create_engine(db_url)

def seed_database():
    print("Starting database seed...")
    engine = get_engine()
    
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. Cameras
        cam1 = Camera(
            id="cam-north-01",
            name="North Gate Entry",
            source_type="rtsp",
            source_uri="rtsp://admin:pass@192.168.1.10/stream1",
            location="North Checkpoint",
            zone="zone-alpha",
            priority=1,
            enabled=True
        )
        cam2 = Camera(
            id="cam-south-01",
            name="South Gate Exit",
            source_type="file",
            source_uri="/data/sample_videos/south_gate.mp4",
            location="South Checkpoint",
            zone="zone-beta",
            priority=2,
            enabled=True
        )
        cam3 = Camera(
            id="cam-perim-01",
            name="Eastern Perimeter",
            source_type="webcam",
            source_uri="0",
            location="Fence Line East",
            zone="zone-alpha",
            priority=3,
            enabled=False
        )
        
        session.merge(cam1)
        session.merge(cam2)
        session.merge(cam3)
        session.commit()
        print("Seeded 3 cameras and 2 zones (via camera zones).")

        # 2. Fence
        fence1 = Fence(
            camera_id="cam-north-01",
            name="Entry Tripwire",
            polygon={"type": "Polygon", "coordinates": [[[0,0], [100,0], [100,100], [0,100], [0,0]]]},
            direction="IN",
            debounce_frames=5,
            enabled=True
        )
        session.add(fence1)
        session.commit()
        print("Seeded 1 fence.")

        # 3. Events
        event1 = Event(
            event_id="evt-1001",
            type="person_detected",
            camera_id="cam-north-01",
            timestamp=datetime.now(timezone.utc),
            track_id="track-10",
            confidence=0.89,
            severity="INFO",
            media_ref="minio://alerts/evt-1001.jpg",
            metadata_={"bbox": [10, 20, 100, 200]}
        )
        event2 = Event(
            event_id="evt-1002",
            type="vehicle_loitering",
            camera_id="cam-south-01",
            timestamp=datetime.now(timezone.utc),
            track_id="track-11",
            confidence=0.95,
            severity="HIGH",
            media_ref="minio://alerts/evt-1002.jpg",
            metadata_={"dwell_time_sec": 120}
        )
        session.add(event1)
        session.add(event2)
        session.commit()
        print("Seeded 2 events.")

        # 4. Watchlist Entry (Plate)
        wl1 = WatchlistEntry(
            type="PLATE",
            label="Stolen Vehicle",
            reference="XYZ-1234",
            enabled=True,
            threshold=0.85
        )
        session.add(wl1)
        session.commit()
        print("Seeded 1 watchlist entry.")

        print("Database seeding completed successfully.")

    except Exception as e:
        session.rollback()
        print(f"Error seeding database: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    seed_database()
