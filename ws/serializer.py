"""Convert World state to JSON-serializable dict for WebSocket broadcast."""
from __future__ import annotations

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
}


class WorldSerializer:
    def world_snapshot(
        self,
        world: World,
        token_tracker: TokenTracker,
        events: list[WorldEvent] | None = None,
    ) -> dict:
        """Full world state snapshot for clients."""
        return {
            "type": "world_state",
            "tick": world.time.tick,
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
        }

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
                result.append(t)
        return result

    def _serialize_npc(self, npc) -> dict:
        return {
            "id": npc.npc_id,
            "name": npc.name,
            "x": npc.x,
            "y": npc.y,
            "color": npc.color,
            "energy": npc.energy,
            "inventory": {
                "wood": npc.inventory.wood,
                "stone": npc.inventory.stone,
                "ore": npc.inventory.ore,
                "food": npc.inventory.food,
                "gold": npc.inventory.gold,
            },
            "last_action": npc.last_action,
            "last_message": npc.last_message,
            "last_message_tick": npc.last_message_tick,
            "is_processing": npc.is_processing,
        }
