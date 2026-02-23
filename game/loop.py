"""Main game loop: world tick, NPC brain loops, God brain loop."""
from __future__ import annotations

import asyncio
import logging
import random
from typing import TYPE_CHECKING

import config
from agents.god_agent import GodAgent
from agents.npc_agent import NPCAgent
from engine.world import NPC, World, create_world
from engine.world_manager import WorldManager
from game.events import EventBus, EventType, WorldEvent
from game.token_tracker import TokenTracker
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
        self.npc_agent = NPCAgent(self.token_tracker)
        self.god_agent = GodAgent(self.token_tracker)
        self._world_lock = asyncio.Lock()
        self._running = False

    # ── Public API ────────────────────────────────────────────────────────────

    async def start(self):
        self._running = True
        logger.info("Game loop starting...")
        tasks = [
            asyncio.create_task(self._world_tick_loop()),
            asyncio.create_task(self._god_brain_loop()),
        ]
        for npc in self.world.npcs:
            tasks.append(asyncio.create_task(self._npc_brain_loop(npc)))
        await asyncio.gather(*tasks, return_exceptions=True)

    async def stop(self):
        self._running = False

    def handle_god_command(self, cmd: dict):
        """Queue a god command from the browser UI."""
        self.world.god.pending_commands.append(cmd)

    def handle_control(self, cmd: dict):
        """Handle game control commands (pause/resume/set_limit/set_api_key)."""
        command = cmd.get("command", "")
        if command == "pause":
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
        """Switch LLM provider at runtime ('gemini' or 'local')."""
        config.LLM_PROVIDER = provider
        if local_url:
            config.LOCAL_LLM_BASE_URL = local_url
            self.npc_agent.reset_local_client()
            self.god_agent.reset_local_client()
        if local_model:
            config.LOCAL_LLM_MODEL = local_model
        logger.info(
            f"LLM provider → {provider}"
            + (f"  model={config.LOCAL_LLM_MODEL}  url={config.LOCAL_LLM_BASE_URL}"
               if provider == "local" else "")
        )

    # ── World tick loop ───────────────────────────────────────────────────────

    async def _world_tick_loop(self):
        """Advances world time and passive effects every WORLD_TICK_SECONDS."""
        while self._running:
            async with self._world_lock:
                self.world.time.advance()
                self.world_manager.apply_passive(self.world)

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
                    continue  # already broadcast

            await self._broadcast()
            await asyncio.sleep(config.WORLD_TICK_SECONDS)

    # ── NPC brain loop ────────────────────────────────────────────────────────

    async def _npc_brain_loop(self, npc: NPC):
        """Each NPC runs its own async loop, deciding actions independently."""
        # Stagger start to avoid all NPCs calling LLM simultaneously
        await asyncio.sleep(random.uniform(1.0, 4.0))

        while self._running:
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

            # Wait before next decision (varies by action type and personality)
            base = random.uniform(config.NPC_MIN_THINK_SECONDS, config.NPC_MAX_THINK_SECONDS)
            # If NPC just spoke, give others time to respond before thinking again
            if npc.last_action == "talk":
                base = random.uniform(3.0, 6.0)
            await asyncio.sleep(base)

    # ── God brain loop ────────────────────────────────────────────────────────

    async def _god_brain_loop(self):
        """God acts on its own schedule, observing the world."""
        await asyncio.sleep(random.uniform(5.0, 10.0))  # delayed first action

        while self._running:
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
        snapshot = self.serializer.world_snapshot(self.world, self.token_tracker, [])
        await self.ws_manager.broadcast(snapshot)

    async def _broadcast_with_events(self, events: list[WorldEvent]):
        snapshot = self.serializer.world_snapshot(self.world, self.token_tracker, events)
        await self.ws_manager.broadcast(snapshot)
