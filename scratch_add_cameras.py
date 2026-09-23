import os
import sys
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add api directory to path to import models
sys.path.append(os.path.join(os.path.dirname(__file__), 'services/api'))
from app.db.models import Camera

async def add_cameras():
    from app.core.config import settings
    db_url = settings.DATABASE_URL
    if "sslmode=require" in db_url:
        db_url = db_url.replace("sslmode=require", "ssl=require")
    if not db_url:
        print("DATABASE_URL not found in environment!")
        return
        
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        cam1 = Camera(
            id="cam_virat_1",
            name="cam 1",
            source_type="file",
            source_uri="/Users/jawwadahmad/IBVAP/data/sample_videos/VIRAT_S_010204_05_000856_000890.mp4",
            location="Test Environment",
            zone="zone-test",
            priority=1,
            enabled=True
        )
        cam2 = Camera(
            id="cam_virat_2",
            name="cam 2",
            source_type="file",
            source_uri="/Users/jawwadahmad/IBVAP/data/sample_videos/VIRAT_S_050201_05_000890_000944.mp4",
            location="Test Environment",
            zone="zone-test",
            priority=2,
            enabled=True
        )
        
        cam3 = Camera(
            id="cam_3",
            name="cam 3",
            source_type="file",
            source_uri="/Users/jawwadahmad/IBVAP/data/sample_videos/16647865_2160_3840_30fps.mp4",
            location="Test Environment",
            zone="zone-test",
            priority=3,
            enabled=True
        )
        cam4 = Camera(
            id="cam_4",
            name="cam 4",
            source_type="file",
            source_uri="/Users/jawwadahmad/IBVAP/data/sample_videos/4118497-hd_1920_1080_24fps.mp4",
            location="Test Environment",
            zone="zone-test",
            priority=4,
            enabled=True
        )
        
        await session.merge(cam1)
        await session.merge(cam2)
        await session.merge(cam3)
        await session.merge(cam4)
        await session.commit()
        print("Successfully added all 4 sample cameras to the database!")

if __name__ == "__main__":
    asyncio.run(add_cameras())
