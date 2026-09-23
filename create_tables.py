import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.db.models import Base
from app.core.config import settings
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'services/api'))

async def init_db():
    db_url = settings.DATABASE_URL
    if "sslmode=require" in db_url:
        db_url = db_url.replace("sslmode=require", "ssl=require")
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created!")

if __name__ == "__main__":
    asyncio.run(init_db())
