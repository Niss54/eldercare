import asyncio
import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket
from pydantic import BaseModel


ALL_TOPICS = "*"


class RealtimeEvent(BaseModel):
    id: str
    channel: str
    event_type: str
    topic: str | None = None
    payload: dict
    timestamp: datetime


class RealtimeService:
    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = {
            "notifications": [],
            "sos": [],
        }
        self.events: list[RealtimeEvent] = []
        self._socket_topics: dict[str, dict[int, set[str]]] = {
            "notifications": {},
            "sos": {},
        }
        self._socket_users: dict[str, dict[int, str]] = {
            "notifications": {},
            "sos": {},
        }
        self._presence_by_user: dict[str, dict[str, int]] = {
            "notifications": {},
            "sos": {},
        }

    @staticmethod
    def _normalize_topic(topic: str | None) -> str | None:
        if topic is None:
            return None
        normalized = topic.strip()
        return normalized or None

    def _is_subscribed(self, websocket: WebSocket, channel: str, topic: str | None) -> bool:
        if topic is None:
            return True
        normalized_topic = self._normalize_topic(topic)
        if normalized_topic is None:
            return True

        channel_topics = self._socket_topics.get(channel, {})
        subscribed = channel_topics.get(id(websocket), set())
        return ALL_TOPICS in subscribed or normalized_topic in subscribed

    def _presence_increment(self, channel: str, user_id: str) -> None:
        channel_presence = self._presence_by_user.setdefault(channel, {})
        channel_presence[user_id] = channel_presence.get(user_id, 0) + 1

    def _presence_decrement(self, channel: str, user_id: str) -> None:
        channel_presence = self._presence_by_user.setdefault(channel, {})
        current = channel_presence.get(user_id, 0)
        if current <= 1:
            channel_presence.pop(user_id, None)
            return
        channel_presence[user_id] = current - 1

    async def connect(self, websocket: WebSocket, channel: str, user_id: str, topics: list[str] | None = None) -> None:
        await websocket.accept()
        self.connections.setdefault(channel, []).append(websocket)
        self._socket_users.setdefault(channel, {})[id(websocket)] = user_id

        normalized_topics = [self._normalize_topic(topic) for topic in (topics or [])]
        normalized_topics = [topic for topic in normalized_topics if topic is not None]
        if not normalized_topics:
            normalized_topics = [ALL_TOPICS]

        self._socket_topics.setdefault(channel, {})[id(websocket)] = set(normalized_topics)
        self._presence_increment(channel, user_id)

    async def disconnect(self, websocket: WebSocket, channel: str) -> None:
        if channel not in self.connections:
            return

        self.connections[channel] = [conn for conn in self.connections[channel] if conn is not websocket]

        channel_users = self._socket_users.setdefault(channel, {})
        user_id = channel_users.pop(id(websocket), None)
        if user_id:
            self._presence_decrement(channel, user_id)

        self._socket_topics.setdefault(channel, {}).pop(id(websocket), None)

    def subscribe(self, websocket: WebSocket, channel: str, topic: str) -> set[str]:
        normalized_topic = self._normalize_topic(topic)
        if normalized_topic is None:
            raise ValueError("topic is required")

        channel_topics = self._socket_topics.setdefault(channel, {})
        socket_topics = channel_topics.setdefault(id(websocket), {ALL_TOPICS})
        if ALL_TOPICS in socket_topics:
            socket_topics.remove(ALL_TOPICS)
        socket_topics.add(normalized_topic)
        return set(socket_topics)

    def unsubscribe(self, websocket: WebSocket, channel: str, topic: str) -> set[str]:
        normalized_topic = self._normalize_topic(topic)
        if normalized_topic is None:
            raise ValueError("topic is required")

        channel_topics = self._socket_topics.setdefault(channel, {})
        socket_topics = channel_topics.setdefault(id(websocket), {ALL_TOPICS})
        socket_topics.discard(normalized_topic)
        if not socket_topics:
            socket_topics.add(ALL_TOPICS)
        return set(socket_topics)

    def presence(self, channel: str) -> dict[str, Any]:
        channel_presence = self._presence_by_user.get(channel, {})
        users = [
            {"user_id": user_id, "connections": connections}
            for user_id, connections in sorted(channel_presence.items())
        ]
        return {
            "channel": channel,
            "online_users": len(channel_presence),
            "active_connections": sum(channel_presence.values()),
            "users": users,
        }

    def topic_subscriptions(self, channel: str) -> dict[str, Any]:
        channel_topics = self._socket_topics.get(channel, {})
        topic_counts: dict[str, int] = {}
        wildcard_subscribers = 0

        for topics in channel_topics.values():
            if ALL_TOPICS in topics:
                wildcard_subscribers += 1
                continue
            for topic in topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

        return {
            "channel": channel,
            "wildcard_subscribers": wildcard_subscribers,
            "topics": dict(sorted(topic_counts.items())),
        }

    def publish(self, channel: str, event_type: str, payload: dict, topic: str | None = None) -> RealtimeEvent:
        normalized_topic = self._normalize_topic(topic)
        event = RealtimeEvent(
            id=secrets.token_urlsafe(12),
            channel=channel,
            event_type=event_type,
            topic=normalized_topic,
            payload=payload,
            timestamp=datetime.now(UTC),
        )
        self.events.append(event)

        sockets = self.connections.get(channel, [])
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop:
            for socket in sockets:
                if not self._is_subscribed(websocket=socket, channel=channel, topic=normalized_topic):
                    continue
                loop.create_task(socket.send_json(event.model_dump()))
        return event

    def get_events(self, channel: str, limit: int = 100, topic: str | None = None) -> list[RealtimeEvent]:
        normalized_topic = self._normalize_topic(topic)
        items = [e for e in self.events if e.channel == channel]
        if normalized_topic is not None:
            items = [e for e in items if e.topic == normalized_topic]
        return items[-limit:]

    def reset(self) -> None:
        self.connections = {"notifications": [], "sos": []}
        self.events.clear()
        self._socket_topics = {"notifications": {}, "sos": {}}
        self._socket_users = {"notifications": {}, "sos": {}}
        self._presence_by_user = {"notifications": {}, "sos": {}}


realtime_service = RealtimeService()
