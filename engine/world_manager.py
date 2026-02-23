"""World state mutations: apply NPC/God/Player actions, passive effects."""
from __future__ import annotations

import random
from typing import Optional

import config
from engine.world import (
    GodEntity, Inventory, NPC, Player, Resource, ResourceType,
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

        # Energy effects for NPCs
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

            # Auto-eat if starving (energy == 0 and has food)
            if npc.energy == 0 and npc.inventory.food > 0:
                npc.inventory.food -= 1
                npc.energy = min(100, npc.energy + config.FOOD_ENERGY_RESTORE)

        # Energy drain for player too
        if world.player:
            phase = world.time.phase
            drain = 1 if phase == "day" else 2
            if world.weather == WeatherType.STORM:
                drain += 1
            world.player.energy = max(0, world.player.energy - drain)

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

        # Food bush regrowth (slower, every 15 ticks)
        if tick % 15 == 0:
            for row in world.tiles:
                for tile in row:
                    if (tile.resource and
                            tile.resource.resource_type == ResourceType.FOOD and
                            tile.resource.quantity < tile.resource.max_quantity):
                        tile.resource.quantity = min(
                            tile.resource.max_quantity,
                            tile.resource.quantity + 1,
                        )

    # ── NPC actions ───────────────────────────────────────────────────────────

    def apply_npc_action(self, npc: NPC, action: dict, world: World) -> list[WorldEvent]:
        """Apply a single NPC action dict to the world. Return generated events."""
        action_type = action.get("action", "idle")
        events: list[WorldEvent] = []
        tick = world.time.tick

        # Store thought if provided
        thought = action.get("thought", "").strip()
        if thought:
            npc.last_thought = thought

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

        elif action_type == "eat":
            events.extend(self._do_eat(npc, world, tick))

        elif action_type == "sleep":
            events.extend(self._do_sleep(npc, world, tick))

        elif action_type == "exchange":
            events.extend(self._do_exchange(npc, action, world, tick))

        elif action_type == "buy_food":
            events.extend(self._do_buy_food(npc, action, world, tick))

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

        rtype = tile.resource.resource_type
        # Cannot gather from exchange/town tiles
        if tile.tile_type == TileType.TOWN:
            return []

        amount = min(2, tile.resource.quantity)
        tile.resource.quantity -= amount

        if rtype == ResourceType.FOOD:
            npc.inventory.food = npc.inventory.food + amount
        else:
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

        # If talking to player, put message in player inbox
        if world.player and target_id == "player":
            world.player.inbox.append(f"{npc.name}: {full_msg}")

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
        if dist > config.NPC_ADJACENT_RADIUS:
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

    def _do_eat(self, npc: NPC, world: World, tick: int) -> list[WorldEvent]:
        if npc.inventory.food <= 0:
            return []
        npc.inventory.food -= 1
        restore = config.FOOD_ENERGY_RESTORE
        npc.energy = min(100, npc.energy + restore)
        npc.last_action = "eat"
        return [WorldEvent(
            event_type=EventType.NPC_ATE,
            tick=tick,
            actor_id=npc.npc_id,
            origin_x=npc.x,
            origin_y=npc.y,
            radius=2,
            payload={"amount": restore},
        )]

    def _do_sleep(self, npc: NPC, world: World, tick: int) -> list[WorldEvent]:
        restore = config.SLEEP_ENERGY_RESTORE
        npc.energy = min(100, npc.energy + restore)
        npc.last_action = "sleep"
        return [WorldEvent(
            event_type=EventType.NPC_SLEPT,
            tick=tick,
            actor_id=npc.npc_id,
            origin_x=npc.x,
            origin_y=npc.y,
            radius=2,
            payload={"amount": restore},
        )]

    def _do_exchange(self, npc: NPC, action: dict, world: World, tick: int) -> list[WorldEvent]:
        """Exchange resources for gold at the exchange building."""
        tile = world.get_tile(npc.x, npc.y)
        if not tile or not tile.is_exchange:
            return []

        item = action.get("exchange_item", "")
        qty = int(action.get("exchange_qty", 0) or 0)
        if not item or qty <= 0:
            return []

        rates = {
            "wood": config.EXCHANGE_RATE_WOOD,
            "stone": config.EXCHANGE_RATE_STONE,
            "ore": config.EXCHANGE_RATE_ORE,
        }
        if item not in rates:
            return []

        npc_has = npc.inventory.get(item)
        if npc_has < qty:
            qty = npc_has  # exchange what we have
        if qty <= 0:
            return []

        gold_earned = qty * rates[item]
        npc.inventory.set(item, npc_has - qty)
        npc.inventory.gold += gold_earned
        npc.last_action = "exchange"

        return [WorldEvent(
            event_type=EventType.NPC_EXCHANGED,
            tick=tick,
            actor_id=npc.npc_id,
            origin_x=npc.x,
            origin_y=npc.y,
            radius=4,
            payload={"item": item, "qty": qty, "gold": gold_earned},
        )]

    def _do_buy_food(self, npc: NPC, action: dict, world: World, tick: int) -> list[WorldEvent]:
        """Buy food with gold at the exchange building."""
        tile = world.get_tile(npc.x, npc.y)
        if not tile or not tile.is_exchange:
            return []

        qty = int(action.get("quantity", 1) or 1)
        qty = max(1, qty)
        cost = qty * config.FOOD_COST_GOLD

        if npc.inventory.gold < cost:
            # Buy as many as we can afford
            qty = npc.inventory.gold // config.FOOD_COST_GOLD
            cost = qty * config.FOOD_COST_GOLD

        if qty <= 0:
            return []

        npc.inventory.gold -= cost
        npc.inventory.food += qty
        npc.last_action = "buy_food"

        return [WorldEvent(
            event_type=EventType.NPC_BOUGHT_FOOD,
            tick=tick,
            actor_id=npc.npc_id,
            origin_x=npc.x,
            origin_y=npc.y,
            radius=4,
            payload={"qty": qty, "gold_spent": cost},
        )]

    # ── Player actions ─────────────────────────────────────────────────────────

    def apply_player_action(self, player: Player, action: dict, world: World) -> list[WorldEvent]:
        """Apply a player action. Returns generated events."""
        action_type = action.get("action", "idle")
        tick = world.time.tick
        events: list[WorldEvent] = []

        if action_type == "move":
            events.extend(self._player_move(player, action, world, tick))
        elif action_type == "gather":
            events.extend(self._player_gather(player, world, tick))
        elif action_type == "talk":
            events.extend(self._player_talk(player, action, world, tick))
        elif action_type == "trade":
            events.extend(self._player_trade(player, action, world, tick))
        elif action_type == "eat":
            events.extend(self._player_eat(player, world, tick))
        elif action_type == "exchange":
            events.extend(self._player_exchange(player, action, world, tick))
        elif action_type == "buy_food":
            events.extend(self._player_buy_food(player, action, world, tick))

        player.last_action = action_type
        return events

    def _player_move(self, player: Player, action: dict, world: World, tick: int) -> list[WorldEvent]:
        dx = max(-1, min(1, int(action.get("dx", 0))))
        dy = max(-1, min(1, int(action.get("dy", 0))))
        new_x, new_y = player.x + dx, player.y + dy

        if not (0 <= new_x < world.width and 0 <= new_y < world.height):
            return []
        new_tile = world.get_tile(new_x, new_y)
        if not new_tile or new_tile.tile_type == TileType.WATER:
            return []

        # Update tile player_here flags
        old_tile = world.get_tile(player.x, player.y)
        if old_tile:
            old_tile.player_here = False

        player.x, player.y = new_x, new_y
        new_tile.player_here = True

        energy_cost = 3 if world.weather == WeatherType.STORM else 2
        player.energy = max(0, player.energy - energy_cost)

        return [WorldEvent(
            event_type=EventType.PLAYER_MOVED,
            tick=tick,
            actor_id="player",
            origin_x=player.x,
            origin_y=player.y,
            radius=2,
            payload={"name": player.name},
        )]

    def _player_gather(self, player: Player, world: World, tick: int) -> list[WorldEvent]:
        tile = world.get_tile(player.x, player.y)
        if not tile or not tile.resource or tile.resource.quantity <= 0:
            return []
        if tile.tile_type == TileType.TOWN:
            return []

        rtype = tile.resource.resource_type
        amount = min(2, tile.resource.quantity)
        tile.resource.quantity -= amount

        if rtype == ResourceType.FOOD:
            player.inventory.food += amount
        else:
            player.inventory.set(rtype.value, player.inventory.get(rtype.value) + amount)

        player.energy = max(0, player.energy - 5)

        return [WorldEvent(
            event_type=EventType.PLAYER_GATHERED,
            tick=tick,
            actor_id="player",
            origin_x=player.x,
            origin_y=player.y,
            radius=3,
            payload={"resource": rtype.value, "amount": amount, "name": player.name},
        )]

    def _player_talk(self, player: Player, action: dict, world: World, tick: int) -> list[WorldEvent]:
        message = str(action.get("message", "")).strip()
        if not message:
            return []
        target_id = action.get("target_id", "")
        player.last_message = message

        # Deliver to NPC inbox if target is specific NPC
        if target_id:
            target = world.get_npc(target_id)
            if target:
                target.memory.add_to_inbox(f"[{player.name}对你说] {message}")

        return [WorldEvent(
            event_type=EventType.PLAYER_SPOKE,
            tick=tick,
            actor_id="player",
            origin_x=player.x,
            origin_y=player.y,
            radius=5,
            payload={"message": message, "target_id": target_id, "name": player.name},
        )]

    def _player_trade(self, player: Player, action: dict, world: World, tick: int) -> list[WorldEvent]:
        target_id = action.get("target_id", "")
        target_npc = world.get_npc(target_id)
        if not target_npc:
            return []

        dist = abs(target_npc.x - player.x) + abs(target_npc.y - player.y)
        if dist > config.NPC_ADJACENT_RADIUS + 1:
            return []

        offer_item = action.get("offer_item", "")
        offer_qty = int(action.get("offer_qty", 0) or 0)
        request_item = action.get("request_item", "")
        request_qty = int(action.get("request_qty", 0) or 0)

        if not offer_item or not request_item or offer_qty <= 0 or request_qty <= 0:
            return []

        player_has = player.inventory.get(offer_item)
        npc_has = target_npc.inventory.get(request_item)

        if player_has < offer_qty or npc_has < request_qty:
            return []

        player.inventory.set(offer_item, player_has - offer_qty)
        player.inventory.set(request_item, player.inventory.get(request_item) + request_qty)
        target_npc.inventory.set(request_item, npc_has - request_qty)
        target_npc.inventory.set(offer_item, target_npc.inventory.get(offer_item) + offer_qty)
        target_npc.last_action = "trade"

        return [WorldEvent(
            event_type=EventType.PLAYER_TRADED,
            tick=tick,
            actor_id="player",
            origin_x=player.x,
            origin_y=player.y,
            radius=5,
            payload={
                "with": target_id,
                "offer_item": offer_item,
                "offer_qty": offer_qty,
                "request_item": request_item,
                "request_qty": request_qty,
                "name": player.name,
            },
        )]

    def _player_eat(self, player: Player, world: World, tick: int) -> list[WorldEvent]:
        if player.inventory.food <= 0:
            return []
        player.inventory.food -= 1
        restore = config.FOOD_ENERGY_RESTORE
        player.energy = min(100, player.energy + restore)
        return []

    def _player_exchange(self, player: Player, action: dict, world: World, tick: int) -> list[WorldEvent]:
        tile = world.get_tile(player.x, player.y)
        if not tile or not tile.is_exchange:
            return []

        item = action.get("exchange_item", "")
        qty = int(action.get("exchange_qty", 0) or 0)
        rates = {
            "wood": config.EXCHANGE_RATE_WOOD,
            "stone": config.EXCHANGE_RATE_STONE,
            "ore": config.EXCHANGE_RATE_ORE,
        }
        if not item or qty <= 0 or item not in rates:
            return []

        player_has = player.inventory.get(item)
        qty = min(qty, player_has)
        if qty <= 0:
            return []

        gold_earned = qty * rates[item]
        player.inventory.set(item, player_has - qty)
        player.inventory.gold += gold_earned
        return []

    def _player_buy_food(self, player: Player, action: dict, world: World, tick: int) -> list[WorldEvent]:
        tile = world.get_tile(player.x, player.y)
        if not tile or not tile.is_exchange:
            return []

        qty = int(action.get("quantity", 1) or 1)
        cost = qty * config.FOOD_COST_GOLD
        if player.inventory.gold < cost:
            qty = player.inventory.gold // config.FOOD_COST_GOLD
            cost = qty * config.FOOD_COST_GOLD
        if qty <= 0:
            return []

        player.inventory.gold -= cost
        player.inventory.food += qty
        return []

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
            if tile and tile.tile_type not in (TileType.WATER, TileType.TOWN):
                try:
                    rtype = ResourceType(rtype_str)
                    if rtype == ResourceType.ORE:
                        max_qty = 5
                    elif rtype == ResourceType.FOOD:
                        max_qty = 5
                    else:
                        max_qty = 10
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
