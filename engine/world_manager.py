"""World state mutations: apply NPC/God actions, passive effects."""
from __future__ import annotations

import random
from typing import Optional

from engine.world import (
    GodEntity, Inventory, NPC, Resource, ResourceType,
    TileType, WeatherType, World,
)
from game.events import EventBus, EventType, WorldEvent


class WorldManager:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._rng = random.Random()

    # ── Passive effects (called every world tick) ─────────────────────────────

    def apply_passive(self, world: World):
        tick = world.time.tick

        # Energy effects
        for npc in world.npcs:
            phase = world.time.phase
            weather = world.weather

            # Night drains more energy
            drain = 1 if phase == "day" else 2
            # Storm drains extra
            if weather == WeatherType.STORM:
                drain += 1

            npc.energy = max(0, npc.energy - drain)
            # Dawn restores a small amount
            if phase == "dawn":
                npc.energy = min(100, npc.energy + 1)

        # Resource regrowth (slow, every 10 ticks)
        if tick % 10 == 0:
            for row in world.tiles:
                for tile in row:
                    if tile.resource and tile.resource.quantity < tile.resource.max_quantity:
                        regrow = 2 if world.weather == WeatherType.RAINY else 1
                        tile.resource.quantity = min(
                            tile.resource.max_quantity,
                            tile.resource.quantity + regrow,
                        )

    # ── NPC actions ───────────────────────────────────────────────────────────

    def apply_npc_action(self, npc: NPC, action: dict, world: World) -> list[WorldEvent]:
        """Apply a single NPC action dict to the world. Return generated events."""
        action_type = action.get("action", "idle")
        events: list[WorldEvent] = []
        tick = world.time.tick

        if action_type == "move":
            events.extend(self._do_move(npc, action, world, tick))

        elif action_type == "gather":
            events.extend(self._do_gather(npc, world, tick))

        elif action_type in ("talk", "interrupt"):
            events.extend(self._do_talk(npc, action, world, tick))

        elif action_type == "trade":
            events.extend(self._do_trade(npc, action, world, tick))

        elif action_type == "rest":
            npc.energy = min(100, npc.energy + 20)
            npc.last_action = "rest"

        elif action_type == "think":
            note = action.get("note", "").strip()
            if note:
                npc.memory.add_note(note)
            npc.last_action = "think"

        else:
            npc.last_action = "idle"

        return events

    def _do_move(self, npc: NPC, action: dict, world: World, tick: int) -> list[WorldEvent]:
        dx = int(action.get("dx", 0))
        dy = int(action.get("dy", 0))
        dx = max(-1, min(1, dx))
        dy = max(-1, min(1, dy))

        new_x = npc.x + dx
        new_y = npc.y + dy

        if not (0 <= new_x < world.width and 0 <= new_y < world.height):
            return []

        new_tile = world.get_tile(new_x, new_y)
        if not new_tile or new_tile.tile_type == TileType.WATER:
            return []

        # Remove from old tile
        old_tile = world.get_tile(npc.x, npc.y)
        if old_tile and npc.npc_id in old_tile.npc_ids:
            old_tile.npc_ids.remove(npc.npc_id)

        npc.x, npc.y = new_x, new_y
        new_tile.npc_ids.append(npc.npc_id)

        energy_cost = 3 if world.weather == WeatherType.STORM else 2
        npc.energy = max(0, npc.energy - energy_cost)
        npc.last_action = "move"

        return [WorldEvent(
            event_type=EventType.NPC_MOVED,
            tick=tick,
            actor_id=npc.npc_id,
            origin_x=npc.x,
            origin_y=npc.y,
            radius=2,
        )]

    def _do_gather(self, npc: NPC, world: World, tick: int) -> list[WorldEvent]:
        tile = world.get_tile(npc.x, npc.y)
        if not tile or not tile.resource or tile.resource.quantity <= 0:
            return []

        amount = min(2, tile.resource.quantity)
        tile.resource.quantity -= amount
        rtype = tile.resource.resource_type
        npc.inventory.set(rtype.value, npc.inventory.get(rtype.value) + amount)
        npc.energy = max(0, npc.energy - 5)
        npc.last_action = "gather"

        events = [WorldEvent(
            event_type=EventType.NPC_GATHERED,
            tick=tick,
            actor_id=npc.npc_id,
            origin_x=npc.x,
            origin_y=npc.y,
            radius=3,
            payload={"resource": rtype.value, "amount": amount},
        )]

        if tile.resource.quantity == 0:
            events.append(WorldEvent(
                event_type=EventType.RESOURCE_DEPLETED,
                tick=tick,
                origin_x=npc.x,
                origin_y=npc.y,
                radius=0,
                payload={},
            ))

        return events

    def _do_talk(self, npc: NPC, action: dict, world: World, tick: int) -> list[WorldEvent]:
        message = str(action.get("message", "")).strip()
        if not message:
            return []
        target_id = action.get("target_id")
        prefix = "[打断] " if action.get("action") == "interrupt" else ""
        full_msg = prefix + message

        npc.last_message = full_msg
        npc.last_message_tick = tick
        npc.last_action = "talk"

        return [WorldEvent(
            event_type=EventType.NPC_SPOKE,
            tick=tick,
            actor_id=npc.npc_id,
            origin_x=npc.x,
            origin_y=npc.y,
            radius=5,
            payload={"message": full_msg, "target_id": target_id},
        )]

    def _do_trade(self, npc: NPC, action: dict, world: World, tick: int) -> list[WorldEvent]:
        target_id = action.get("target_id", "")
        target_npc = world.get_npc(target_id)
        if not target_npc:
            return []

        dist = abs(target_npc.x - npc.x) + abs(target_npc.y - npc.y)
        if dist > 1:
            return []

        offer_item = action.get("offer_item", "")
        offer_qty = int(action.get("offer_qty", 0) or 0)
        request_item = action.get("request_item", "")
        request_qty = int(action.get("request_qty", 0) or 0)

        if not offer_item or not request_item or offer_qty <= 0 or request_qty <= 0:
            return []

        npc_has = npc.inventory.get(offer_item)
        target_has = target_npc.inventory.get(request_item)

        if npc_has < offer_qty or target_has < request_qty:
            return []

        # Execute trade
        npc.inventory.set(offer_item, npc_has - offer_qty)
        npc.inventory.set(request_item, npc.inventory.get(request_item) + request_qty)
        target_npc.inventory.set(request_item, target_has - request_qty)
        target_npc.inventory.set(offer_item, target_npc.inventory.get(offer_item) + offer_qty)

        npc.last_action = "trade"
        target_npc.last_action = "trade"

        return [WorldEvent(
            event_type=EventType.NPC_TRADED,
            tick=tick,
            actor_id=npc.npc_id,
            origin_x=npc.x,
            origin_y=npc.y,
            radius=5,
            payload={
                "with": target_id,
                "offer_item": offer_item,
                "offer_qty": offer_qty,
                "request_item": request_item,
                "request_qty": request_qty,
            },
        )]

    # ── God actions ───────────────────────────────────────────────────────────

    def apply_god_action(self, action: dict, world: World) -> list[WorldEvent]:
        action_type = action.get("action", "")
        tick = world.time.tick
        events: list[WorldEvent] = []

        if action_type == "set_weather":
            new_weather_str = action.get("weather", "sunny")
            try:
                new_weather = WeatherType(new_weather_str)
                world.weather = new_weather
                commentary = action.get("commentary", "")
                world.god.last_commentary = commentary

                events.append(WorldEvent(
                    event_type=EventType.WEATHER_CHANGED,
                    tick=tick,
                    payload={"weather": new_weather.value, "commentary": commentary},
                ))
            except ValueError:
                pass

        elif action_type == "spawn_resource":
            x = int(action.get("x", 0) or 0)
            y = int(action.get("y", 0) or 0)
            rtype_str = action.get("resource_type", "wood")
            qty = int(action.get("quantity", 5) or 5)
            commentary = action.get("commentary", "")

            tile = world.get_tile(x, y)
            if tile and tile.tile_type not in (TileType.WATER,):
                try:
                    rtype = ResourceType(rtype_str)
                    max_qty = 10 if rtype != ResourceType.ORE else 5
                    tile.resource = Resource(rtype, min(qty, max_qty), max_qty)
                    world.god.last_commentary = commentary

                    events.append(WorldEvent(
                        event_type=EventType.RESOURCE_SPAWNED,
                        tick=tick,
                        payload={
                            "resource_type": rtype_str,
                            "x": x, "y": y,
                            "quantity": qty,
                            "commentary": commentary,
                        },
                    ))
                except ValueError:
                    pass

        return events

    def apply_direct_god_command(self, cmd: dict, world: World) -> list[WorldEvent]:
        """Apply a god command received directly from browser UI (no LLM)."""
        command = cmd.get("command", "")
        action: dict = {}

        if command == "set_weather":
            action = {
                "action": "set_weather",
                "weather": cmd.get("value", "sunny"),
                "commentary": "玩家通过控制面板调整了天气",
            }
        elif command == "spawn_resource":
            action = {
                "action": "spawn_resource",
                "resource_type": cmd.get("resource_type", "wood"),
                "x": cmd.get("x", 0),
                "y": cmd.get("y", 0),
                "quantity": cmd.get("quantity", 5),
                "commentary": "玩家通过控制面板召唤了资源",
            }

        if action:
            return self.apply_god_action(action, world)
        return []
