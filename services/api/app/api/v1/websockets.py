import asyncio
import json
import logging
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
import os

from redis.asyncio import Redis

logger = logging.getLogger(__name__)
router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._redis = None
        self._pubsub = None
        self._listen_task = None
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")
        
        # Start Redis listener if this is the first client
        if len(self.active_connections) == 1:
            await self._start_redis_listener()

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")
            
        # Stop listener if no clients
        if len(self.active_connections) == 0:
            self._stop_redis_listener()

    async def broadcast(self, message: str):
        failed_connections = []
        for connection in self.active_connections:
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_text(message)
                else:
                    failed_connections.append(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                failed_connections.append(connection)
                
        # Cleanup failed connections
        for conn in failed_connections:
            self.disconnect(conn)

    async def _start_redis_listener(self):
        try:
            self._redis = Redis.from_url(self.redis_url, decode_responses=True)
            self._pubsub = self._redis.pubsub()
            await self._pubsub.subscribe("ibvap_events")
            self._listen_task = asyncio.create_task(self._listen_to_redis())
            logger.info("Started Redis subscription for WebSockets.")
        except Exception as e:
            logger.error(f"Failed to start Redis listener: {e}")

    def _stop_redis_listener(self):
        if self._listen_task:
            self._listen_task.cancel()
            self._listen_task = None
        if self._pubsub:
            asyncio.create_task(self._pubsub.unsubscribe("ibvap_events"))
        if self._redis:
            asyncio.create_task(self._redis.close())
            self._redis = None
        logger.info("Stopped Redis subscription for WebSockets.")

    async def _listen_to_redis(self):
        while True:
            try:
                if not self._pubsub:
                    # Try to reconnect
                    self._redis = Redis.from_url(self.redis_url, decode_responses=True)
                    self._pubsub = self._redis.pubsub()
                    await self._pubsub.subscribe("ibvap_events")
                    logger.info("Reconnected Redis subscription for WebSockets.")
                    
                message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    await self.broadcast(message["data"])
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Redis listener error: {e}")
                self._pubsub = None
                if self._redis:
                    await self._redis.close()
                    self._redis = None
                await asyncio.sleep(2.0) # Wait before reconnecting

manager = ConnectionManager()

@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Simple ping/pong heartbeat to keep connection alive
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
