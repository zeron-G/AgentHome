"""FastAPI entry point: WebSocket endpoint, static file serving, game startup."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from game.loop import GameLoop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AgentHome")
game_loop = GameLoop()

# ── Static files ──────────────────────────────────────────────────────────────

FRONTEND_DIR = Path(__file__).parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await game_loop.ws_manager.connect(ws)

    # Send immediate world snapshot on connect
    try:
        snapshot = game_loop.serializer.world_snapshot(
            game_loop.world, game_loop.token_tracker, []
        )
        await game_loop.ws_manager.send_to(ws, snapshot)
    except Exception:
        pass

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")

            if msg_type == "god_command":
                game_loop.handle_god_command(msg)

            elif msg_type == "control":
                game_loop.handle_control(msg)

            elif msg_type == "god_direct":
                # Direct god action (bypass LLM, immediate)
                game_loop.handle_god_command(msg)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await game_loop.ws_manager.disconnect(ws)


# ── App lifecycle ─────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    logger.info("Starting AgentHome game loop...")
    asyncio.create_task(game_loop.start())


@app.on_event("shutdown")
async def shutdown():
    await game_loop.stop()
