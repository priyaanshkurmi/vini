import json
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from emotion.engine import emotion

ws_router = APIRouter()
logger    = logging.getLogger("vini.websocket")

connected_clients: list[WebSocket] = []


@ws_router.websocket("/ws/avatar")
async def avatar_websocket(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    logger.info("Avatar connected.")

    try:
        async def heartbeat():
            while True:
                try:
                    await ws.send_text(json.dumps({
                        "type":    "heartbeat",
                        "emotion": emotion.to_dict(),
                    }))
                    await asyncio.sleep(1)
                except Exception:
                    break

        async def listen():
            while True:
                try:
                    data = await ws.receive_text()
                    msg  = json.loads(data)
                    logger.info(f"Avatar message: {msg}")
                except WebSocketDisconnect:
                    break
                except Exception:
                    break

        await asyncio.gather(heartbeat(), listen())

    except WebSocketDisconnect:
        logger.info("Avatar disconnected.")
    finally:
        if ws in connected_clients:
            connected_clients.remove(ws)


async def broadcast(payload: dict):
    dead = []
    for ws in connected_clients:
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            dead.append(ws)
    for ws in dead:
        connected_clients.remove(ws)


async def broadcast_amplitude(frames: list[float]):
    for amp in frames:
        await broadcast({"type": "speaking", "amplitude": amp, "animation": "talking"})
        await asyncio.sleep(0.02)
    await broadcast({"type": "idle", "animation": "idle"})