from fastapi import APIRouter

api_router = APIRouter()

from app.api.v1 import faces, plates, cameras, fences, events, websockets, system

api_router.include_router(faces.router, prefix="/watchlists/faces", tags=["faces"])
api_router.include_router(plates.router, prefix="/watchlists/plates", tags=["plates"])
api_router.include_router(cameras.router, prefix="/cameras", tags=["cameras"])
api_router.include_router(fences.router, prefix="/fences", tags=["fences"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(websockets.router, prefix="/ws/events", tags=["websockets"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
