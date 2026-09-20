from fastapi import APIRouter

api_router = APIRouter()

# Note: Individual routers for cameras, events, etc., will be included here later.
# e.g., api_router.include_router(cameras.router, prefix="/cameras", tags=["cameras"])
