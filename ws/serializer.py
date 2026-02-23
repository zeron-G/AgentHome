"""Convert World state to JSON-serializable dict for WebSocket broadcast."""
from __future__ import annotations

from engine.world import World
from game.events import WorldEvent
from game.token_tracker import TokenTracker


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
                    "t": tile.tile_type.value[0],  # g/w/r/f (first letter)
                }
                if tile.resource and tile.resource.quantity > 0:
                    t["r"] = tile.resource.resource_type.value[0]  # w/s/o
                    t["q"] = tile.resource.quantity
                    t["mq"] = tile.resource.max_quantity
                if tile.npc_ids:
                    t["n"] = tile.npc_ids
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
            },
            "last_action": npc.last_action,
            "last_message": npc.last_message,
            "last_message_tick": npc.last_message_tick,
            "is_processing": npc.is_processing,
        }
