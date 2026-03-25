import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.metrics import metrics_recorder
from src.modules.consent_access.evaluator import consent_policy_evaluator
from src.modules.identity_access.models import Role
from src.modules.realtime.service import realtime_service

router = APIRouter()


async def _authorize_websocket(websocket: WebSocket, channel: str) -> bool:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return False

    # Lazy import avoids circular imports between auth and websocket routers.
    from src.interfaces.api.v1.auth import identity_service

    try:
        claims = identity_service.decode_access_token(token)
    except Exception:
        await websocket.close(code=4401)
        return False

    permissions = set(claims.get("permissions", []))
    if channel == "notifications":
        if "notification:read" not in permissions:
            await websocket.close(code=4403)
            return False
        default_scope = "notification:read"
    elif channel == "sos":
        if "sos:respond" not in permissions and "sos:trigger" not in permissions:
            await websocket.close(code=4403)
            return False
        default_scope = "sos:respond"
    else:
        await websocket.close(code=4404)
        return False

    subject_user_id = websocket.query_params.get("subject_user_id")
    required_scope = websocket.query_params.get("scope") or default_scope
    if subject_user_id:
        allowed = consent_policy_evaluator.evaluate(
            actor_user_id=claims["sub"],
            actor_role=Role(claims["role"]),
            subject_user_id=subject_user_id,
            required_scope=required_scope,
        )
        if not allowed:
            await websocket.close(code=4403)
            return False

    websocket.state.claims = claims
    return True


async def _channel_loop(websocket: WebSocket, channel: str, initial_topic: str | None = None):
    authorized = await _authorize_websocket(websocket=websocket, channel=channel)
    if not authorized:
        return

    claims = websocket.state.claims
    await realtime_service.connect(
        websocket=websocket,
        channel=channel,
        user_id=claims["sub"],
        topics=[initial_topic] if initial_topic else None,
    )
    metrics_recorder.observe_websocket_connected(channel)
    await websocket.send_json(
        {
            "event_type": "ws.connected",
            "channel": channel,
            "topic": initial_topic,
            "user_id": claims["sub"],
        }
    )
    disconnect_code = 1000
    try:
        while True:
            packet = await websocket.receive()
            if packet.get("type") == "websocket.disconnect":
                raise WebSocketDisconnect()

            text = packet.get("text")
            if text is None:
                continue

            parsed: dict | None = None
            try:
                candidate = json.loads(text)
                if isinstance(candidate, dict):
                    parsed = candidate
            except json.JSONDecodeError:
                parsed = None

            if parsed is None:
                realtime_service.publish(channel=channel, event_type="client.message", payload={"message": text})
                continue

            action = str(parsed.get("action", "")).strip().lower()
            if action == "subscribe":
                topic = str(parsed.get("topic", "")).strip()
                if not topic:
                    await websocket.send_json({"event_type": "ws.error", "detail": "topic is required"})
                    continue
                subscriptions = sorted(realtime_service.subscribe(websocket=websocket, channel=channel, topic=topic))
                await websocket.send_json({"event_type": "ws.subscribed", "channel": channel, "topic": topic, "subscriptions": subscriptions})
                continue

            if action == "unsubscribe":
                topic = str(parsed.get("topic", "")).strip()
                if not topic:
                    await websocket.send_json({"event_type": "ws.error", "detail": "topic is required"})
                    continue
                subscriptions = sorted(realtime_service.unsubscribe(websocket=websocket, channel=channel, topic=topic))
                await websocket.send_json({"event_type": "ws.unsubscribed", "channel": channel, "topic": topic, "subscriptions": subscriptions})
                continue

            if action == "ping":
                await websocket.send_json({"event_type": "ws.pong", "channel": channel, "presence": realtime_service.presence(channel)})
                continue

            if action == "publish":
                event_type = str(parsed.get("event_type") or "client.message").strip()
                payload = parsed.get("payload")
                payload_dict = payload if isinstance(payload, dict) else {"message": str(payload)}
                topic = parsed.get("topic")
                topic_value = str(topic).strip() if isinstance(topic, str) else None
                realtime_service.publish(channel=channel, event_type=event_type, payload=payload_dict, topic=topic_value)
                continue

            realtime_service.publish(channel=channel, event_type="client.message", payload={"message": text})
    except WebSocketDisconnect:
        disconnect_code = 1001
    finally:
        await realtime_service.disconnect(websocket, channel)
        metrics_recorder.observe_websocket_disconnected(channel=channel, code=disconnect_code)


@router.websocket("/ws/notifications")
async def notification_channel(websocket: WebSocket):
    await _channel_loop(websocket, "notifications")


@router.websocket("/ws/sos")
async def sos_channel(websocket: WebSocket):
    await _channel_loop(websocket, "sos")


@router.websocket("/ws/{channel}/{topic}")
async def topic_channel(websocket: WebSocket, channel: str, topic: str):
    await _channel_loop(websocket, channel, initial_topic=topic)
