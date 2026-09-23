from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

db_url = settings.DATABASE_URL
if "sslmode=require" in db_url:
    db_url = db_url.replace("sslmode=require", "ssl=require")

engine = create_async_engine(db_url, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
