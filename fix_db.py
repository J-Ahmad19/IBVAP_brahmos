import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'services/api'))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def fix_db():
    db_url = settings.DATABASE_URL
    if "sslmode=require" in db_url:
        db_url = db_url.replace("sslmode=require", "ssl=require")
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE events ADD COLUMN status VARCHAR(50) DEFAULT 'NEW';"))
            print("Successfully added status column.")
        except Exception as e:
            print("Error adding column (maybe it already exists?):", e)
    
if __name__ == "__main__":
    asyncio.run(fix_db())
