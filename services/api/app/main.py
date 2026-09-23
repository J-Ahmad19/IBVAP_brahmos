from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.v1.router import api_router
from app.core.subscriber import EventSubscriber

subscriber = EventSubscriber()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await subscriber.start()
    yield
    # Shutdown
    await subscriber.stop()

app = FastAPI(title="IBVAP API", lifespan=lifespan)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"status": "ok"}
