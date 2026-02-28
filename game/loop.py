"""Main game loop: world tick, NPC brain loops, God brain loop, player actions."""
from __future__ import annotations

import asyncio
import logging
import random
from typing import TYPE_CHECKING

import config
from agents.god_agent import GodAgent
from agents.npc_agent import NPCAgent
from config_narrative import DAILY_NPC_CONFIG
from engine.world import NPC, World, create_world
from engine.world_manager import WorldManager
from game.events import EventBus, EventType, WorldEvent
from game.token_tracker import TokenTracker
from rag import JSONRAGStorage
from ws.manager import WSManager
from ws.serializer import WorldSerializer

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class GameLoop:
    def __init__(self):
        self.world: World = create_world()
        self.event_bus = EventBus()
        self.world_manager = WorldManager(self.event_bus)
        self.token_tracker = TokenTracker()
        self.ws_manager = WSManager()
        self.serializer = WorldSerializer()

        # RAG storage (JSON-based, swappable)
        self.rag = JSONRAGStorage()

        self.npc_agent = NPCAgent(self.token_tracker, rag_storage=self.rag)
        self.god_agent = GodAgent(self.token_tracker)

        self._world_lock = asyncio.Lock()
        self._running = False            # server-alive flag
        self._simulation_running = False # world ticking + agent brains running

        # Cancellable simulation tasks
        self._sim_tasks: list[asyncio.Task] = []

    # ── Public API ────────────────────────────────────────────────────────────

    async def start(self):
        """Start the server listener. Simulation does NOT auto-start."""
        self._running = True
        logger.info("GameLoop server started (simulation paused — click Start to begin).")
        # Send initial snapshot so clients see the frozen world
        await self._broadcast()
        # Keep server alive
        while self._running:
            await asyncio.sleep(1.0)

    async def stop(self):
        self._running = False
        await self._stop_simulation()

    # ── Simulation start / stop ───────────────────────────────────────────────

    async def start_simulation(self):
        if self._simulation_running:
            return
        self._simulation_running = True
        logger.info("Simulation started.")
        tasks = [
            asyncio.create_task(self._world_tick_loop()),
            asyncio.create_task(self._god_brain_loop()),
        ]
        for npc in self.world.npcs:
            tasks.append(asyncio.create_task(self._npc_brain_loop(npc)))
        self._sim_tasks = tasks

    async def _stop_simulation(self):
        self._simulation_running = False
        for t in self._sim_tasks:
            t.cancel()
        self._sim_tasks.clear()
        logger.info("Simulation stopped.")

    async def stop_simulation(self):
        await self._stop_simulation()

    # ── Control commands ──────────────────────────────────────────────────────

    def handle_god_command(self, cmd: dict):
        """Queue a god command from the browser UI."""
        self.world.god.pending_commands.append(cmd)

    def handle_control(self, cmd: dict):
        """Handle game control commands."""
        command = cmd.get("command", "")

        if command == "start_simulation":
            asyncio.create_task(self._start_and_broadcast())
        elif command == "stop_simulation":
            asyncio.create_task(self._stop_and_broadcast())
        elif command == "pause":
            self.token_tracker._paused = True
        elif command == "resume":
            self.token_tracker.resume()
        elif command == "set_limit":
            new_limit = int(cmd.get("value", config.DEFAULT_TOKEN_LIMIT))
            self.token_tracker.set_limit(new_limit)
        elif command == "set_api_key":
            new_key = cmd.get("value", "").strip()
            if new_key:
                self.update_api_key(new_key)
        elif command == "save_game":
            asyncio.create_task(self._save_game())
        elif command == "delete_saves":
            self.rag.delete_all()
            logger.info("All saves deleted.")
        elif command == "delete_npc_memory":
            npc_id = cmd.get("value", "").strip()
            if npc_id:
                self.rag.delete_npc_memory(npc_id)
        elif command == "toggle_god_mode":
            if self.world.player:
                self.world.player.is_god_mode = not self.world.player.is_god_mode
        elif command == "update_setting":
            self._apply_setting(cmd.get("key", ""), cmd.get("value"))
        elif command == "set_show_thoughts":
            val = cmd.get("value", True)
            config.SHOW_NPC_THOUGHTS = bool(val)
        elif command == "set_player_name":
            name = str(cmd.get("value", "")).strip()
            if name and self.world.player:
                self.world.player.name = name

    async def _start_and_broadcast(self):
        await self.start_simulation()
        await self._broadcast()

    async def _stop_and_broadcast(self):
        await self._stop_simulation()
        await self._broadcast()

    def _apply_setting(self, key: str, value):
        """Apply a hot-modifiable config setting by key name."""
        try:
            if key == "world_tick_seconds":
                config.WORLD_TICK_SECONDS = max(0.5, float(value))
            elif key == "npc_min_think":
                config.NPC_MIN_THINK_SECONDS = max(1.0, float(value))
            elif key == "npc_max_think":
                config.NPC_MAX_THINK_SECONDS = max(2.0, float(value))
            elif key == "god_min_think":
                config.GOD_MIN_THINK_SECONDS = max(5.0, float(value))
            elif key == "god_max_think":
                config.GOD_MAX_THINK_SECONDS = max(10.0, float(value))
            elif key == "npc_hearing_radius":
                config.NPC_HEARING_RADIUS = max(1, int(value))
            elif key == "food_energy_restore":
                config.FOOD_ENERGY_RESTORE = max(1, int(value))
            elif key == "sleep_energy_restore":
                config.SLEEP_ENERGY_RESTORE = max(1, int(value))
            elif key == "exchange_rate_wood":
                config.EXCHANGE_RATE_WOOD = max(1, int(value))
            elif key == "exchange_rate_stone":
                config.EXCHANGE_RATE_STONE = max(1, int(value))
            elif key == "exchange_rate_ore":
                config.EXCHANGE_RATE_ORE = max(1, int(value))
            elif key == "food_cost_gold":
                config.FOOD_COST_GOLD = max(1, int(value))
            elif key == "npc_vision_radius":
                config.NPC_VISION_RADIUS = max(1, int(value))
            elif key == "show_npc_thoughts":
                config.SHOW_NPC_THOUGHTS = bool(value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid setting {key}={value}: {e}")

    async def handle_player_action(self, msg: dict):
        """Process a player action message from a WebSocket client."""
        if not self.world.player:
            return

        player = self.world.player

        # God mode: route weather/resource commands as god actions
        if player.is_god_mode and msg.get("action") in ("set_weather", "spawn_resource"):
            cmd = dict(msg)
            self.handle_god_command(cmd)
            return

        events: list[WorldEvent] = []
        async with self._world_lock:
            events = self.world_manager.apply_player_action(player, msg, self.world)

        for evt in events:
            self.event_bus.dispatch(evt, self.world)

        await self._broadcast_with_events(events if events else [])

    async def _save_game(self):
        """Persist current world state snapshot to RAG storage."""
        try:
            state = self.serializer.world_snapshot(
                self.world, self.token_tracker, [], self._simulation_running
            )
            self.rag.save_game_state(state)
            logger.info("Game state saved.")
        except Exception as e:
            logger.error(f"Save error: {e}")

    def update_api_key(self, new_key: str):
        """Hot-reload the Gemini API key for all agents."""
        config.GEMINI_API_KEY = new_key
        self.npc_agent.update_api_key(new_key)
        self.god_agent.update_api_key(new_key)

    def update_provider(
        self,
        provider: str,
        local_url: str | None = None,
        local_model: str | None = None,
    ):
        """Switch LLM provider at runtime ('claude', 'gemini', or 'local')."""
        config.LLM_PROVIDER = provider
        if provider == "claude":
            self.npc_agent.reset_claude_client()
            self.god_agent.reset_claude_client()
        if local_url:
            config.LOCAL_LLM_BASE_URL = local_url
            self.npc_agent.reset_local_client()
            self.god_agent.reset_local_client()
        if local_model:
            config.LOCAL_LLM_MODEL = local_model
        extra = ""
        if provider == "local":
            extra = f"  model={config.LOCAL_LLM_MODEL}  url={config.LOCAL_LLM_BASE_URL}"
        elif provider == "claude":
            extra = f"  model={config.ANTHROPIC_MODEL}"
        logger.info(f"LLM provider → {provider}{extra}")

    # ── World tick loop ───────────────────────────────────────────────────────

    async def _world_tick_loop(self):
        """Advances world time and passive effects every WORLD_TICK_SECONDS."""
        while self._simulation_running:
            market_event = None
            async with self._world_lock:
                self.world.time.advance()
                self.world_manager.apply_passive(self.world)

                # Update market prices every MARKET_UPDATE_INTERVAL ticks
                tick = self.world.time.tick
                if tick % config.MARKET_UPDATE_INTERVAL == 0:
                    market_event = self.world_manager.update_market(self.world)
            if market_event:
                self.event_bus.dispatch(market_event, self.world)

            # Apply any queued direct god commands (immediate, no LLM)
            if self.world.god.pending_commands:
                direct_cmds = list(self.world.god.pending_commands)
                self.world.god.pending_commands.clear()
                events: list[WorldEvent] = []
                async with self._world_lock:
                    for cmd in direct_cmds:
                        evts = self.world_manager.apply_direct_god_command(cmd, self.world)
                        events.extend(evts)
                for evt in events:
                    self.event_bus.dispatch(evt, self.world)
                if events:
                    await self._broadcast_with_events(events)
                    await asyncio.sleep(config.WORLD_TICK_SECONDS)
                    continue

            # Spawn dialogue option generation tasks if needed
            if getattr(self.world, "_pending_dialogue_option_gen", False) and self.world.player:
                self.world._pending_dialogue_option_gen = False
                for dialogue in list(self.world.player.dialogue_queue):
                    if dialogue.get("reply_options") is None:
                        asyncio.create_task(self._fill_dialogue_options(dialogue))

            await self._broadcast()
            await asyncio.sleep(config.WORLD_TICK_SECONDS)

    # ── NPC brain loop ────────────────────────────────────────────────────────

    async def _npc_brain_loop(self, npc: NPC):
        """Each NPC runs its own async loop, deciding actions independently."""
        # Stagger start to avoid all NPCs calling LLM simultaneously
        await asyncio.sleep(random.uniform(1.0, 4.0))

        while self._simulation_running:
            if self.token_tracker.paused:
                await asyncio.sleep(2.0)
                continue

            try:
                action = await self.npc_agent.process(npc, self.world)

                if action.get("action") not in ("idle", None):
                    events: list[WorldEvent] = []
                    async with self._world_lock:
                        events = self.world_manager.apply_npc_action(npc, action, self.world)

                    for evt in events:
                        self.event_bus.dispatch(evt, self.world)

                    if events:
                        await self._broadcast_with_events(events)

            except Exception as e:
                logger.error(f"[{npc.name}] brain loop error: {e}")

            # Wait before next decision
            base = random.uniform(config.NPC_MIN_THINK_SECONDS, config.NPC_MAX_THINK_SECONDS)
            if npc.last_action == "talk":
                base = random.uniform(3.0, 6.0)
            # 日常NPC（旷/木/岚/石）think频率降低以节省API调用
            daily_cfg = DAILY_NPC_CONFIG.get(npc.npc_id)
            if daily_cfg:
                base *= daily_cfg.get("think_interval_multiplier", 1.0)
            await asyncio.sleep(base)

    # ── God brain loop ────────────────────────────────────────────────────────

    async def _god_brain_loop(self):
        """God acts on its own schedule, observing the world."""
        await asyncio.sleep(random.uniform(5.0, 10.0))

        while self._simulation_running:
            if self.token_tracker.paused:
                await asyncio.sleep(2.0)
                continue

            try:
                action = await self.god_agent.process(self.world.god, self.world)
                if action:
                    events: list[WorldEvent] = []
                    async with self._world_lock:
                        events = self.world_manager.apply_god_action(action, self.world)
                    for evt in events:
                        self.event_bus.dispatch(evt, self.world)
                    if events:
                        await self._broadcast_with_events(events)

            except Exception as e:
                logger.error(f"[God] brain loop error: {e}")

            await asyncio.sleep(
                random.uniform(config.GOD_MIN_THINK_SECONDS, config.GOD_MAX_THINK_SECONDS)
            )

    # ── Broadcast helpers ─────────────────────────────────────────────────────

    async def _broadcast(self):
        snapshot = self.serializer.world_snapshot(
            self.world, self.token_tracker, [], self._simulation_running
        )
        await self.ws_manager.broadcast(snapshot)

    async def _fill_dialogue_options(self, dialogue: dict):
        """Async task: call GodAgent to generate quick-reply options for a player dialogue."""
        try:
            options = await self.god_agent.generate_dialogue_options(
                dialogue["from_name"], dialogue["message"], self.world
            )
            dialogue["reply_options"] = options
            # Broadcast updated player state (dialogue_queue now has options)
            await self._broadcast_with_events([])
        except Exception as e:
            logger.warning(f"[GameLoop] _fill_dialogue_options error: {e}")
            dialogue["reply_options"] = ["好的，继续说", "我没有兴趣", "能详细说说吗？"]

    async def _broadcast_with_events(self, events: list[WorldEvent]):
        snapshot = self.serializer.world_snapshot(
            self.world, self.token_tracker, events, self._simulation_running
        )
        await self.ws_manager.broadcast(snapshot)
