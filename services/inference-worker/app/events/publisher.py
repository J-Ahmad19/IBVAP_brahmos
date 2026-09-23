import json
import logging
import asyncio
from typing import AsyncGenerator
from redis.asyncio import Redis

from app.events.schema import Event

logger = logging.getLogger(__name__)

class EventPublisher:
    """
    Manages the Redis Pub/Sub connection for events.
    """
    def __init__(self, redis_url: str = "redis://localhost:6379", channel: str = "ibvap_events"):
        self.redis_url = redis_url
        self.channel = channel
        self._redis = None
        self._buffer = []
        self._max_buffer_size = 1000

    async def connect(self):
        if self._redis is None:
            try:
                self._redis = Redis.from_url(self.redis_url, decode_responses=True)
                logger.info(f"Connected to Redis at {self.redis_url}")
                await self._flush_buffer()
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._redis = None

    async def _flush_buffer(self):
        if not self._redis or not self._buffer:
            return
            
        logger.info(f"Flushing {len(self._buffer)} buffered events to Redis")
        while self._buffer:
            event = self._buffer[0]
            try:
                event_json = event.json()
                await self._redis.publish(self.channel, event_json)
                self._buffer.pop(0)
            except Exception as e:
                logger.error(f"Failed to flush event {event.event_id}: {e}")
                self._redis = None # Disconnect
                break

    async def disconnect(self):
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def publish(self, event: Event):
        """Publishes an event to the Redis channel."""
        if not self._redis:
            await self.connect()
            
        if self._redis:
            try:
                event_json = event.json()
                await self._redis.publish(self.channel, event_json)
                logger.debug(f"Published event {event.event_id} to {self.channel}")
                return
            except Exception as e:
                logger.error(f"Failed to publish event {event.event_id}: {e}")
                self._redis = None # Mark as disconnected
        
        # Buffer if not published
        if len(self._buffer) < self._max_buffer_size:
            self._buffer.append(event)
            logger.warning(f"Buffered event {event.event_id} due to Redis unavailability")
        else:
            logger.error(f"Event buffer full, dropping event {event.event_id}")

    async def subscribe(self) -> AsyncGenerator[Event, None]:
        """
        Subscribes to the event channel and yields Event objects.
        Used primarily by the API service to listen to events.
        """
        if not self._redis:
            await self.connect()
            
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self.channel)
        logger.info(f"Subscribed to {self.channel}")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        event = Event(**event_data)
                        yield event
                    except Exception as e:
                        logger.error(f"Failed to decode event from Redis: {e}")
        finally:
            await pubsub.unsubscribe(self.channel)
