"""Convert World state to JSON-serializable dict for WebSocket broadcast."""
from __future__ import annotations

import config
from engine.world import ResourceType, TileType, World
from game.events import WorldEvent
from game.token_tracker import TokenTracker

# Compact single-letter codes
_TILE_LETTER = {
    TileType.GRASS: "g",
    TileType.WATER: "w",
    TileType.ROCK: "r",
    TileType.FOREST: "f",
    TileType.TOWN: "o",
}
_RESOURCE_LETTER = {
    ResourceType.WOOD: "w",
    ResourceType.STONE: "s",
    ResourceType.ORE: "o",
    ResourceType.FOOD: "f",
    ResourceType.HERB: "h",
}


class WorldSerializer:
    def world_snapshot(
        self,
        world: World,
        token_tracker: TokenTracker,
        events: list[WorldEvent] | None = None,
        simulation_running: bool = False,
    ) -> dict:
        """Full world state snapshot for clients."""
        snapshot: dict = {
            "type": "world_state",
            "tick": world.time.tick,
            "simulation_running": simulation_running,
            "time": {
                "hour": round(world.time.hour, 1),
                "day": world.time.day,
                "phase": world.time.phase,
                "time_str": world.time.time_str,
            },
            "weather": world.weather.value,
            "tiles": self._serialize_tiles(world),
            "npcs": [self._serialize_npc(npc) for npc in world.npcs],
            "god": {
                "commentary": world.god.last_commentary,
            },
            "events": [e.to_dict(world) for e in (events or [])],
            "token_usage": token_tracker.snapshot(),
            "settings": self._serialize_settings(),
            "market": self._serialize_market(world),
        }

        # Include player if present
        if world.player:
            snapshot["player"] = self._serialize_player(world.player)
        else:
            snapshot["player"] = None

        return snapshot

    def _serialize_tiles(self, world: World) -> list[dict]:
        result = []
        for row in world.tiles:
            for tile in row:
                t: dict = {
                    "x": tile.x,
                    "y": tile.y,
                    "t": _TILE_LETTER.get(tile.tile_type, "g"),
                }
                if tile.resource and tile.resource.quantity > 0:
                    t["r"] = _RESOURCE_LETTER.get(tile.resource.resource_type, "?")
                    t["q"] = tile.resource.quantity
                    t["mq"] = tile.resource.max_quantity
                if tile.npc_ids:
                    t["n"] = tile.npc_ids
                if tile.is_exchange:
                    t["e"] = 1
                if tile.player_here:
                    t["p"] = 1
                if tile.furniture:
                    t["f"] = tile.furniture
                result.append(t)
        return result

    def _serialize_npc(self, npc) -> dict:
        d: dict = {
            "id": npc.npc_id,
            "name": npc.name,
            "x": npc.x,
            "y": npc.y,
            "color": npc.color,
            "energy": npc.energy,
            "inventory": npc.inventory.to_dict(),
            "last_action": npc.last_action,
            "last_message": npc.last_message,
            "last_message_tick": npc.last_message_tick,
            "is_processing": npc.is_processing,
            "equipped": getattr(npc, "equipped", None),
            "inv_count": npc.inventory.total_items(),
            "inv_max": config.INVENTORY_MAX_SLOTS,
            "pending_proposals": len(getattr(npc, "pending_proposals", [])),
            # Hierarchical decision-making state (Level-1 strategic layer)
            "goal": getattr(npc, "goal", ""),
            "plan": list(getattr(npc, "plan", [])),
        }
        # Conditionally include inner thought
        if config.SHOW_NPC_THOUGHTS and getattr(npc, "last_thought", ""):
            d["thought"] = npc.last_thought
        # Include profile summary if available
        prof = getattr(npc, "profile", None)
        if prof:
            d["profile"] = {
                "title": prof.title,
                "backstory": prof.backstory,
                "personality": prof.personality,
                "goals": list(prof.goals),
                "speech_style": prof.speech_style,
                "relationships": dict(prof.relationships),
            }
        return d

    def _serialize_player(self, player) -> dict:
        # Latest pending dialogue (with reply_options if available)
        dialogue_queue = getattr(player, "dialogue_queue", [])
        latest_dialogue = None
        for d in reversed(dialogue_queue):
            if d.get("reply_options") is not None or len(dialogue_queue) > 0:
                latest_dialogue = {
                    "from_id": d["from_id"],
                    "from_name": d["from_name"],
                    "message": d["message"],
                    "tick": d["tick"],
                    "reply_options": d.get("reply_options"),  # None while loading
                }
                break

        return {
            "id": player.player_id,
            "name": player.name,
            "x": player.x,
            "y": player.y,
            "energy": player.energy,
            "is_god_mode": player.is_god_mode,
            "last_action": player.last_action,
            "last_message": player.last_message,
            "inventory": player.inventory.to_dict(),
            "inbox": list(player.inbox[-10:]),  # last 10 messages
            "equipped": getattr(player, "equipped", None),
            "inv_count": player.inventory.total_items(),
            "inv_max": config.INVENTORY_MAX_SLOTS,
            "dialogue": latest_dialogue,
        }

    def _serialize_market(self, world: World) -> dict:
        """Serialize market prices and history for the economy panel."""
        market = world.market
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
        return {
            "prices": prices,
            "history": {item: list(hist) for item, hist in market.history.items()},
            "last_update_tick": market.last_update_tick,
        }

    def _serialize_settings(self) -> dict:
        """Current hot-modifiable settings for client sync."""
        return {
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
        }
