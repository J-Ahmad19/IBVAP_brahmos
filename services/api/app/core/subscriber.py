import json
import logging
import asyncio
import os
from redis.asyncio import Redis

# Hack to import Event from inference worker schema
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../.."))
try:
    from services.inference_worker.app.events.schema import Event
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), "../../../../services/inference-worker"))
    from app.events.schema import Event

logger = logging.getLogger(__name__)

class EventSubscriber:
    """
    Subscribes to Redis Event Bus and persists events to PostgreSQL.
    """
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.channel = "ibvap_events"
        self._redis = None
        self._running = False
        self._task = None

    async def connect(self):
        if self._redis is None:
            self._redis = Redis.from_url(self.redis_url, decode_responses=True)
            logger.info(f"Subscriber connected to Redis at {self.redis_url}")

    async def start(self):
        await self.connect()
        self._running = True
        self._task = asyncio.create_task(self._listen())
        logger.info("EventSubscriber background task started.")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        if self._redis:
            await self._redis.close()
            self._redis = None
        logger.info("EventSubscriber stopped.")

    async def _listen(self):
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self.channel)
        
        try:
            while self._running:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        event = Event(**event_data)
                        await self._persist_event(event)
                    except Exception as e:
                        logger.error(f"Error processing event from Redis: {e}")
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(self.channel)

    async def _persist_event(self, event: Event):
        """
        Persists the event to the PostgreSQL database.
        (Mocked for prototype since no async_engine is currently configured in the API service).
        """
        # In a complete implementation, we'd acquire an AsyncSession here and insert into DBEvent
        logger.info(f"[PERSIST] Saving event {event.event_id} (Type: {event.type.value}) to PostgreSQL.")
        
        # Example of what would happen:
        # async with AsyncSessionLocal() as db:
        #     db_event = DBEvent(
        #         event_id=event.event_id,
        #         type=event.type.value,
        #         ...
        #     )
        #     db.add(db_event)
        #     await db.commit()
