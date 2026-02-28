"""FastAPI entry point: WebSocket endpoint, static file serving, game startup."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import config
from game.loop import GameLoop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AgentHome")
game_loop = GameLoop()

# ── Static files (optional — HTML frontend removed, Godot client is primary) ──

FRONTEND_DIR = Path(__file__).parent / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
async def index():
    if FRONTEND_DIR.is_dir() and (FRONTEND_DIR / "index.html").exists():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
    return JSONResponse({"status": "ok", "client": "Use Godot client to connect via WebSocket"})


# ── Settings API ──────────────────────────────────────────────────────────────

@app.get("/api/settings")
async def get_settings():
    return JSONResponse({
        "api_key_set": bool(config.GEMINI_API_KEY),
        "model_name": config.MODEL_NAME,
        "token_limit": game_loop.token_tracker.session_limit,
        "llm_provider": config.LLM_PROVIDER,
        "local_llm_base_url": config.LOCAL_LLM_BASE_URL,
        "local_llm_model": config.LOCAL_LLM_MODEL,
        # Hot-modifiable settings
        "show_npc_thoughts": config.SHOW_NPC_THOUGHTS,
        "npc_vision_radius": config.NPC_VISION_RADIUS,
        "world_tick_seconds": config.WORLD_TICK_SECONDS,
        "npc_min_think": config.NPC_MIN_THINK_SECONDS,
        "npc_max_think": config.NPC_MAX_THINK_SECONDS,
        "god_min_think": config.GOD_MIN_THINK_SECONDS,
        "god_max_think": config.GOD_MAX_THINK_SECONDS,
        "npc_hearing_radius": config.NPC_HEARING_RADIUS,
        "food_energy_restore": config.FOOD_ENERGY_RESTORE,
        "sleep_energy_restore": config.SLEEP_ENERGY_RESTORE,
        "exchange_rate_wood": config.EXCHANGE_RATE_WOOD,
        "exchange_rate_stone": config.EXCHANGE_RATE_STONE,
        "exchange_rate_ore": config.EXCHANGE_RATE_ORE,
        "food_cost_gold": config.FOOD_COST_GOLD,
        "player_name": (
            game_loop.world.player.name if game_loop.world.player else config.PLAYER_NAME
        ),
        "simulation_running": game_loop._simulation_running,
    })


@app.post("/api/settings")
async def post_settings(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid JSON"}, status_code=400)

    # Gemini API key
    if "api_key" in data and str(data["api_key"]).strip():
        game_loop.update_api_key(str(data["api_key"]).strip())

    # Gemini model name
    if "model_name" in data and str(data["model_name"]).strip():
        config.MODEL_NAME = str(data["model_name"]).strip()

    # Token limit
    if "token_limit" in data:
        try:
            game_loop.token_tracker.set_limit(int(data["token_limit"]))
        except (ValueError, TypeError):
            pass

    # LLM provider switch (claude / gemini / local)
    if "llm_provider" in data:
        provider = str(data["llm_provider"]).strip()
        if provider in ("claude", "gemini", "local"):
            local_url = str(data.get("local_llm_base_url", "") or "").strip() or None
            local_model = str(data.get("local_llm_model", "") or "").strip() or None
            game_loop.update_provider(provider, local_url, local_model)

    # Hot-modifiable settings routed through _apply_setting
    hot_keys = [
        "world_tick_seconds", "npc_min_think", "npc_max_think",
        "god_min_think", "god_max_think", "npc_hearing_radius",
        "food_energy_restore", "sleep_energy_restore",
        "exchange_rate_wood", "exchange_rate_stone", "exchange_rate_ore",
        "food_cost_gold", "npc_vision_radius", "show_npc_thoughts",
    ]
    for key in hot_keys:
        if key in data:
            game_loop._apply_setting(key, data[key])

    # Player name
    if "player_name" in data and game_loop.world.player:
        name = str(data["player_name"]).strip()
        if name:
            game_loop.world.player.name = name

    return JSONResponse({"ok": True})


# ── NPC Profile API ───────────────────────────────────────────────────────────

@app.get("/api/npc_profiles")
async def get_npc_profiles():
    """Return all NPC profiles."""
    profiles = []
    for npc in game_loop.world.npcs:
        prof = getattr(npc, "profile", None)
        if prof:
            profiles.append(prof.to_dict())
        else:
            profiles.append({"npc_id": npc.npc_id, "name": npc.name})
    return JSONResponse(profiles)


@app.put("/api/npc_profiles/{npc_id}")
async def update_npc_profile(npc_id: str, request: Request):
    """Hot-update a single NPC's profile."""
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid JSON"}, status_code=400)

    npc = game_loop.world.get_npc(npc_id)
    if not npc:
        return JSONResponse({"ok": False, "error": "NPC not found"}, status_code=404)

    from engine.world import NPCProfile
    data["npc_id"] = npc_id  # ensure id matches
    try:
        profile = NPCProfile.from_dict(data)
        profile.apply_to_npc(npc)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.get("/api/npc_profiles/export")
async def export_npc_profiles():
    """Export all NPC profiles as JSON array."""
    profiles = []
    for npc in game_loop.world.npcs:
        prof = getattr(npc, "profile", None)
        if prof:
            profiles.append(prof.to_dict())
    return JSONResponse(profiles)


@app.post("/api/npc_profiles/import")
async def import_npc_profiles(request: Request):
    """Import and apply NPC profiles from JSON array."""
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid JSON"}, status_code=400)

    from engine.world import NPCProfile
    updated = []
    for item in data:
        npc_id = item.get("npc_id", "")
        npc = game_loop.world.get_npc(npc_id)
        if npc:
            try:
                profile = NPCProfile.from_dict(item)
                profile.apply_to_npc(npc)
                updated.append(npc_id)
            except Exception:
                pass
    return JSONResponse({"ok": True, "updated": updated})


# ── Market API ────────────────────────────────────────────────────────────────

@app.get("/api/market")
async def get_market():
    """Return current market state."""
    market = game_loop.world.market
    prices = {}
    for item, mp in market.prices.items():
        prices[item] = {
            "base": mp.base,
            "current": round(mp.current, 2),
            "min": mp.min_p,
            "max": mp.max_p,
            "trend": mp.trend,
            "change_pct": mp.change_pct,
        }
    return JSONResponse({
        "prices": prices,
        "history": {item: list(hist) for item, hist in market.history.items()},
        "last_update_tick": market.last_update_tick,
    })


# ── Saves API ─────────────────────────────────────────────────────────────────

@app.get("/api/saves")
async def get_saves():
    return JSONResponse(game_loop.rag.list_save_info())


@app.post("/api/saves/delete")
async def delete_all_saves():
    game_loop.rag.delete_all()
    return JSONResponse({"ok": True})


@app.post("/api/saves/delete_memory")
async def delete_npc_memory(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid JSON"}, status_code=400)
    npc_id = str(data.get("npc_id", "")).strip()
    if not npc_id:
        return JSONResponse({"ok": False, "error": "npc_id required"}, status_code=400)
    game_loop.rag.delete_npc_memory(npc_id)
    return JSONResponse({"ok": True})


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await game_loop.ws_manager.connect(ws)

    # Send immediate world snapshot on connect
    try:
        snapshot = game_loop.serializer.world_snapshot(
            game_loop.world,
            game_loop.token_tracker,
            [],
            game_loop._simulation_running,
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

            elif msg_type == "god_direct":
                game_loop.handle_god_command(msg)

            elif msg_type == "control":
                game_loop.handle_control(msg)

            elif msg_type == "player_action":
                await game_loop.handle_player_action(msg)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await game_loop.ws_manager.disconnect(ws)


# ── App lifecycle ─────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    logger.info("Starting AgentHome server (simulation paused at startup).")
    asyncio.create_task(game_loop.start())


@app.on_event("shutdown")
async def shutdown():
    await game_loop.stop()
