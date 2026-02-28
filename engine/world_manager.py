"""World state mutations: apply NPC/God/Player actions, passive effects."""
from __future__ import annotations

import random
from typing import Optional

import config
from engine.world import (
    GodEntity, Inventory, NPC, Player, Resource, ResourceType,
    TileType, WeatherType, World, MarketPrice,
)
from game.events import EventBus, EventType, WorldEvent


class WorldManager:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._rng = random.Random()

    # ── Market update ──────────────────────────────────────────────────────────

    def update_market(self, world: World) -> Optional[WorldEvent]:
        """Recalculate floating prices. Called every MARKET_UPDATE_INTERVAL ticks."""
        tick = world.time.tick
        market = world.market

        # Count supply on the map + in NPC inventories
        supply: dict[str, float] = {item: 0.0 for item in config.MARKET_BASE_PRICES}
        for row in world.tiles:
            for tile in row:
                if tile.resource:
                    rt = tile.resource.resource_type.value
                    if rt in supply:
                        supply[rt] += tile.resource.quantity

        for npc in world.npcs:
            inv = npc.inventory
            for item in supply:
                supply[item] += inv.get(item)

        # Demand proxy: how many NPCs are low on each resource
        demand: dict[str, float] = {item: 1.0 for item in config.MARKET_BASE_PRICES}
        for npc in world.npcs:
            inv = npc.inventory
            # Low food → demand food more
            if inv.food < 3:
                demand["food"] = demand.get("food", 1.0) + 2.0
            # Low energy → demand potions / bread
            if npc.energy < 40:
                demand["potion"] = demand.get("potion", 1.0) + 1.5
                demand["bread"] = demand.get("bread", 1.0) + 1.0

        # Weather modifier
        weather = world.weather
        weather_mod: dict[str, float] = {}
        if weather == WeatherType.STORM:
            weather_mod["food"] = 1.4
            weather_mod["herb"] = 0.7
        elif weather == WeatherType.RAINY:
            weather_mod["herb"] = 1.2
            weather_mod["wood"] = 1.1

        for item, mp in market.prices.items():
            s = max(supply.get(item, 0) + 1, 1)     # avoid /0
            d = demand.get(item, 1.0)
            wmod = weather_mod.get(item, 1.0)
            noise = 1.0 + self._rng.uniform(-config.MARKET_VOLATILITY, config.MARKET_VOLATILITY)

            target = mp.base * (d / (s / 10)) * wmod * noise
            target = max(mp.min_p, min(mp.max_p, target))

            # Exponential smoothing
            new_current = round(
                mp.current * (1 - config.MARKET_SMOOTHING) + target * config.MARKET_SMOOTHING, 2
            )
            mp.current = new_current

            # Record history (keep last 30)
            hist = market.history.setdefault(item, [])
            hist.append(new_current)
            if len(hist) > 30:
                hist.pop(0)

        market.last_update_tick = tick

        return WorldEvent(
            event_type=EventType.MARKET_UPDATED,
            tick=tick,
            payload={"tick": tick},
        )

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

            # Expire pending proposals older than 10 ticks
            npc.pending_proposals = [
                p for p in npc.pending_proposals
                if tick - p.get("tick", 0) <= 10
            ]

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
            tile = world.get_tile(npc.x, npc.y)
            rest_energy = 20
            if tile and tile.furniture == "chair":
                rest_energy = config.FURNITURE_EFFECTS.get("chair", {}).get("rest_energy", 35)
            npc.energy = min(100, npc.energy + rest_energy)
            npc.last_action = "rest"
            npc.last_action_result = f"休息了一会儿，恢复了{rest_energy}体力"

        elif action_type == "think":
            note = action.get("note", "").strip()
            if note:
                npc.memory.add_note(note)
            npc.last_action = "think"
            npc.last_action_result = "记录了一些想法"

        elif action_type == "eat":
            events.extend(self._do_eat(npc, world, tick))

        elif action_type == "sleep":
            events.extend(self._do_sleep(npc, world, tick))

        elif action_type == "exchange":
            events.extend(self._do_exchange(npc, action, world, tick))

        elif action_type == "buy_food":
            events.extend(self._do_buy_food(npc, action, world, tick))

        elif action_type == "craft":
            events.extend(self._do_craft(npc, action, world, tick))

        elif action_type == "sell":
            events.extend(self._do_sell(npc, action, world, tick))

        elif action_type == "buy":
            events.extend(self._do_buy(npc, action, world, tick))

        elif action_type == "use_item":
            events.extend(self._do_use_item(npc, action, world, tick))

        elif action_type == "propose_trade":
            events.extend(self._do_propose_trade(npc, action, world, tick))

        elif action_type == "accept_trade":
            events.extend(self._do_accept_trade(npc, action, world, tick))

        elif action_type == "reject_trade":
            events.extend(self._do_reject_trade(npc, action, world, tick))

        elif action_type == "counter_trade":
            events.extend(self._do_counter_trade(npc, action, world, tick))

        elif action_type == "build":
            events.extend(self._do_build(npc, action, world, tick))

        else:
            npc.last_action = "idle"
            npc.last_action_result = "发呆了一会儿"

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
        if npc.equipped == "rope":
            rope_save = config.ITEM_EFFECTS.get("rope", {}).get("move_energy_save", 0)
            energy_cost = max(0, energy_cost - rope_save)
        npc.energy = max(0, npc.energy - energy_cost)
        npc.last_action = "move"
        tile_desc = new_tile.tile_type.value if new_tile else "未知"
        npc.last_action_result = f"移动到了({npc.x},{npc.y})，这里是{tile_desc}"

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
            npc.last_action_result = "这里没有可采集的资源"
            return []

        rtype = tile.resource.resource_type
        # Cannot gather from exchange/town tiles
        if tile.tile_type == TileType.TOWN:
            return []

        base_amount = 2
        if npc.equipped == "tool":
            base_amount *= config.ITEM_EFFECTS.get("tool", {}).get("gather_bonus", 1)
        amount = min(base_amount, tile.resource.quantity)

        # Capacity check
        if not npc.inventory.has_space(amount):
            amount = config.INVENTORY_MAX_SLOTS - npc.inventory.total_items()
        if amount <= 0:
            return []
        tile.resource.quantity -= amount

        if rtype == ResourceType.FOOD:
            npc.inventory.food = npc.inventory.food + amount
        elif rtype == ResourceType.HERB:
            npc.inventory.herb += amount
        else:
            npc.inventory.set(rtype.value, npc.inventory.get(rtype.value) + amount)

        npc.energy = max(0, npc.energy - 5)
        npc.last_action = "gather"
        npc.last_action_result = f"采集了{amount}个{rtype.value}"

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
        target_name = target_id or "周围的人"
        if world.player and target_id == "player":
            target_name = world.player.name
        else:
            t_npc = world.get_npc(target_id) if target_id else None
            if t_npc:
                target_name = t_npc.name
        npc.last_action_result = f"对{target_name}说了话"

        # If talking to player, push to dialogue_queue for reply UI
        if world.player and target_id == "player":
            world.player.inbox.append(f"{npc.name}: {full_msg}")
            world.player.dialogue_queue.append({
                "from_id": npc.npc_id,
                "from_name": npc.name,
                "message": full_msg,
                "tick": tick,
                "reply_options": None,  # filled by GodAgent async
            })
            world._pending_dialogue_option_gen = True

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
        npc.last_action_result = f"与{target_npc.name}交易了{offer_qty}{offer_item}换{request_qty}{request_item}"
        target_npc.last_action = "trade"
        target_npc.last_action_result = f"与{npc.name}交易了{request_qty}{request_item}换{offer_qty}{offer_item}"

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
            npc.last_action_result = "没有食物可以吃"
            return []
        npc.inventory.food -= 1
        restore = config.FOOD_ENERGY_RESTORE
        npc.energy = min(100, npc.energy + restore)
        npc.last_action = "eat"
        npc.last_action_result = f"吃了食物，恢复了{restore}体力"
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
        tile = world.get_tile(npc.x, npc.y)
        if tile and tile.furniture == "bed":
            restore = config.FURNITURE_EFFECTS.get("bed", {}).get("sleep_energy", config.SLEEP_ENERGY_RESTORE)
        else:
            restore = config.SLEEP_ENERGY_RESTORE
        npc.energy = min(100, npc.energy + restore)
        npc.last_action = "sleep"
        bed_str = "在床上" if (tile and tile.furniture == "bed") else ""
        npc.last_action_result = f"{bed_str}睡了一觉，恢复了{restore}体力"
        return [WorldEvent(
            event_type=EventType.NPC_SLEPT,
            tick=tick,
            actor_id=npc.npc_id,
            origin_x=npc.x,
            origin_y=npc.y,
            radius=2,
            payload={"amount": restore, "on_bed": tile is not None and tile.furniture == "bed"},
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
        npc.last_action_result = f"用{qty}个{item}换了{gold_earned}金币"

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

        # Capacity check
        if not npc.inventory.has_space(qty):
            qty = config.INVENTORY_MAX_SLOTS - npc.inventory.total_items()
            cost = qty * config.FOOD_COST_GOLD
        if qty <= 0:
            return []

        npc.inventory.gold -= cost
        npc.inventory.food += qty
        npc.last_action = "buy_food"
        npc.last_action_result = f"花{cost}金币买了{qty}个食物"

        return [WorldEvent(
            event_type=EventType.NPC_BOUGHT_FOOD,
            tick=tick,
            actor_id=npc.npc_id,
            origin_x=npc.x,
            origin_y=npc.y,
            radius=4,
            payload={"qty": qty, "gold_spent": cost},
        )]

    def _do_craft(self, npc: NPC, action: dict, world: World, tick: int) -> list[WorldEvent]:
        """Craft an item from a recipe. Nearby table doubles output."""
        item = action.get("craft_item", "").strip()
        recipe = config.CRAFTING_RECIPES.get(item)
        if not recipe:
            return []

        # Check materials
        for mat, needed in recipe.items():
            if npc.inventory.get(mat) < needed:
                return []

        # Check for nearby table (3-tile Manhattan radius)
        table_bonus = 1
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                if abs(dx) + abs(dy) <= 3:
                    t = world.get_tile(npc.x + dx, npc.y + dy)
                    if t and t.furniture == "table":
                        table_bonus = config.FURNITURE_EFFECTS.get("table", {}).get("craft_bonus", 1)
                        break
            if table_bonus > 1:
                break

        qty = table_bonus

        # Capacity check
        if not npc.inventory.has_space(qty):
            return []

        # Consume materials
        for mat, needed in recipe.items():
            npc.inventory.set(mat, npc.inventory.get(mat) - needed)

        # Produce item
        npc.inventory.set(item, npc.inventory.get(item) + qty)
        npc.last_action = "craft"
        npc.last_action_result = f"制造了{qty}个{item}"
        actor_id = getattr(npc, "npc_id", getattr(npc, "player_id", "unknown"))
        evt = EventType.PLAYER_CRAFTED if actor_id == "player" else EventType.NPC_CRAFTED

        return [WorldEvent(
            event_type=evt,
            tick=tick,
            actor_id=actor_id,
            origin_x=npc.x,
            origin_y=npc.y,
            radius=3,
            payload={"item": item, "qty": qty},
        )]

    def _do_sell(self, npc: NPC, action: dict, world: World, tick: int) -> list[WorldEvent]:
        """Sell items at market price (must be at exchange)."""
        tile = world.get_tile(npc.x, npc.y)
        if not tile or not tile.is_exchange:
            return []

        item = action.get("sell_item", "").strip()
        qty = int(action.get("sell_qty", 0) or 0)
        if not item or qty <= 0:
            return []

        npc_has = npc.inventory.get(item)
        qty = min(qty, npc_has)
        if qty <= 0:
            return []

        # Use market price if available, else fall back to legacy exchange rates
        mp = world.market.prices.get(item)
        if mp:
            price = mp.current
        else:
            rates = {"wood": config.EXCHANGE_RATE_WOOD, "stone": config.EXCHANGE_RATE_STONE,
                     "ore": config.EXCHANGE_RATE_ORE}
            price = rates.get(item, 1.0)

        gold_earned = round(qty * price, 1)
        npc.inventory.set(item, npc_has - qty)
        npc.inventory.gold = round(npc.inventory.gold + gold_earned, 1)
        npc.last_action = "sell"
        npc.last_action_result = f"以{price:.1f}金/个卖出了{qty}个{item}，获得{gold_earned:.0f}金"
        actor_id = getattr(npc, "npc_id", getattr(npc, "player_id", "unknown"))
        evt = EventType.PLAYER_SOLD if actor_id == "player" else EventType.NPC_SOLD

        return [WorldEvent(
            event_type=evt,
            tick=tick,
            actor_id=actor_id,
            origin_x=npc.x,
            origin_y=npc.y,
            radius=4,
            payload={"item": item, "qty": qty, "gold": gold_earned, "price": price},
        )]

    def _do_buy(self, npc: NPC, action: dict, world: World, tick: int) -> list[WorldEvent]:
        """Buy items at market price (must be at exchange)."""
        tile = world.get_tile(npc.x, npc.y)
        if not tile or not tile.is_exchange:
            return []

        item = action.get("buy_item", "").strip()
        qty = int(action.get("buy_qty", 0) or 0)
        if not item or qty <= 0:
            return []

        mp = world.market.prices.get(item)
        if not mp:
            # Fallback: food only
            if item == "food":
                return self._do_buy_food(npc, {"quantity": qty}, world, tick)
            return []

        total_cost = round(qty * mp.current, 1)
        if npc.inventory.gold < total_cost:
            # Buy as many as affordable
            qty = int(npc.inventory.gold / mp.current)
            total_cost = round(qty * mp.current, 1)
        if qty <= 0:
            return []

        # Capacity check
        if not npc.inventory.has_space(qty):
            qty = config.INVENTORY_MAX_SLOTS - npc.inventory.total_items()
            total_cost = round(qty * mp.current, 1)
        if qty <= 0:
            return []

        npc.inventory.gold = round(npc.inventory.gold - total_cost, 1)
        npc.inventory.set(item, npc.inventory.get(item) + qty)
        npc.last_action = "buy"
        npc.last_action_result = f"以{mp.current:.1f}金/个买了{qty}个{item}，花了{total_cost:.0f}金"
        actor_id = getattr(npc, "npc_id", getattr(npc, "player_id", "unknown"))
        evt = EventType.PLAYER_BOUGHT if actor_id == "player" else EventType.NPC_BOUGHT

        return [WorldEvent(
            event_type=evt,
            tick=tick,
            actor_id=actor_id,
            origin_x=npc.x,
            origin_y=npc.y,
            radius=4,
            payload={"item": item, "qty": qty, "gold": total_cost, "price": mp.current},
        )]

    def _do_equip_item(self, character, item: str, world: World, tick: int) -> list[WorldEvent]:
        """Unified equip logic for NPC or Player. Routes tool/rope into equipment slot."""
        if character.inventory.get(item) < 1:
            return []

        old = character.equipped
        if old and old != item:
            # Return old item to inventory if space available
            character.inventory.set(old, character.inventory.get(old) + 1)

        character.inventory.set(item, character.inventory.get(item) - 1)
        character.equipped = item

        actor_id = getattr(character, "npc_id", getattr(character, "player_id", "unknown"))
        evt_type = EventType.NPC_EQUIPPED if hasattr(character, "npc_id") else EventType.PLAYER_EQUIPPED
        return [WorldEvent(
            event_type=evt_type,
            tick=tick,
            actor_id=actor_id,
            origin_x=character.x,
            origin_y=character.y,
            radius=2,
            payload={"item": item, "replaced": old},
        )]

    def _do_use_item(self, npc: NPC, action: dict, world: World, tick: int) -> list[WorldEvent]:
        """Use a consumable or equip a tool/rope."""
        item = action.get("use_item", "").strip()
        if not item or npc.inventory.get(item) <= 0:
            npc.last_action_result = f"没有{item}可以使用" if item else "没有指定物品"
            return []

        effects = config.ITEM_EFFECTS.get(item, {})

        if "energy" in effects:
            restore = effects["energy"]
            npc.energy = min(100, npc.energy + restore)
            npc.inventory.set(item, npc.inventory.get(item) - 1)
            npc.last_action = "use_item"
            npc.last_action_result = f"使用了{item}，恢复了{restore}体力"
            return [WorldEvent(
                event_type=EventType.NPC_USED_ITEM,
                tick=tick,
                actor_id=npc.npc_id,
                origin_x=npc.x,
                origin_y=npc.y,
                radius=2,
                payload={"item": item, "effect": f"恢复{restore}体力"},
            )]
        elif "gather_bonus" in effects or "move_energy_save" in effects:
            # Equip slot items
            events = self._do_equip_item(npc, item, world, tick)
            if events:
                npc.last_action = "use_item"
                npc.last_action_result = f"装备了{item}"
            return events

        return []

    def _do_propose_trade(self, npc: NPC, action: dict, world: World, tick: int) -> list[WorldEvent]:
        """Send a trade proposal to a nearby NPC."""
        target_id = action.get("target_id", "")
        target_npc = world.get_npc(target_id)
        if not target_npc:
            return []

        dist = abs(target_npc.x - npc.x) + abs(target_npc.y - npc.y)
        if dist > config.NPC_ADJACENT_RADIUS + 2:  # allow a bit more range for proposals
            return []

        offer_item = action.get("offer_item", "")
        offer_qty = int(action.get("offer_qty", 0) or 0)
        request_item = action.get("request_item", "")
        request_qty = int(action.get("request_qty", 0) or 0)
        if not offer_item or not request_item or offer_qty <= 0 or request_qty <= 0:
            return []

        # Verify proposer has what they're offering
        if npc.inventory.get(offer_item) < offer_qty:
            return []

        proposal = {
            "from_id": npc.npc_id,
            "offer_item": offer_item,
            "offer_qty": offer_qty,
            "request_item": request_item,
            "request_qty": request_qty,
            "tick": tick,
            "round": 1,
        }
        target_npc.pending_proposals.append(proposal)
        npc.last_action = "propose_trade"
        npc.last_action_result = f"向{target_npc.name}提出交易：{offer_qty}{offer_item}换{request_qty}{request_item}"

        return [WorldEvent(
            event_type=EventType.TRADE_PROPOSED,
            tick=tick,
            actor_id=npc.npc_id,
            origin_x=npc.x,
            origin_y=npc.y,
            radius=5,
            payload={
                "target_id": target_id,
                "offer_item": offer_item, "offer_qty": offer_qty,
                "request_item": request_item, "request_qty": request_qty,
            },
        )]

    def _find_proposal(self, npc: NPC, action: dict) -> Optional[dict]:
        """Find the pending proposal from proposal_from or the oldest one."""
        from_id = action.get("proposal_from", "").strip()
        if from_id:
            for p in npc.pending_proposals:
                if p.get("from_id") == from_id:
                    return p
        if npc.pending_proposals:
            return npc.pending_proposals[0]
        return None

    def _do_accept_trade(self, npc: NPC, action: dict, world: World, tick: int) -> list[WorldEvent]:
        """Accept a pending trade proposal."""
        proposal = self._find_proposal(npc, action)
        if not proposal:
            return []

        from_id = proposal["from_id"]
        from_npc = world.get_npc(from_id)
        if not from_npc:
            npc.pending_proposals.remove(proposal)
            return []

        # Verify both parties still have the items
        give_item = proposal["request_item"]   # npc gives this
        give_qty = proposal["request_qty"]
        recv_item = proposal["offer_item"]     # npc receives this
        recv_qty = proposal["offer_qty"]

        if (npc.inventory.get(give_item) < give_qty or
                from_npc.inventory.get(recv_item) < recv_qty):
            npc.pending_proposals.remove(proposal)
            return []

        # Execute
        npc.inventory.set(give_item, npc.inventory.get(give_item) - give_qty)
        npc.inventory.set(recv_item, npc.inventory.get(recv_item) + recv_qty)
        from_npc.inventory.set(recv_item, from_npc.inventory.get(recv_item) - recv_qty)
        from_npc.inventory.set(give_item, from_npc.inventory.get(give_item) + give_qty)

        npc.pending_proposals.remove(proposal)
        npc.last_action = "accept_trade"
        npc.last_action_result = f"接受了{from_npc.name}的交易，给出{give_qty}{give_item}获得{recv_qty}{recv_item}"
        from_npc.last_action = "trade"
        from_npc.last_action_result = f"{npc.name}接受了交易，获得{give_qty}{give_item}给出{recv_qty}{recv_item}"

        return [WorldEvent(
            event_type=EventType.TRADE_ACCEPTED,
            tick=tick,
            actor_id=npc.npc_id,
            origin_x=npc.x,
            origin_y=npc.y,
            radius=5,
            payload={"from_id": from_id, "give_item": give_item, "give_qty": give_qty,
                     "recv_item": recv_item, "recv_qty": recv_qty},
        )]

    def _do_reject_trade(self, npc: NPC, action: dict, world: World, tick: int) -> list[WorldEvent]:
        """Reject a pending trade proposal and notify proposer."""
        proposal = self._find_proposal(npc, action)
        if not proposal:
            return []

        from_id = proposal["from_id"]
        from_npc = world.get_npc(from_id)
        npc.pending_proposals.remove(proposal)
        npc.last_action = "reject_trade"
        from_name = from_npc.name if from_npc else from_id
        npc.last_action_result = f"拒绝了{from_name}的交易提案"

        # Notify proposer via inbox
        if from_npc:
            from_npc.memory.add_to_inbox(
                f"{npc.name} 拒绝了你提出的交易 "
                f"({proposal['offer_qty']}{proposal['offer_item']}↔"
                f"{proposal['request_qty']}{proposal['request_item']})"
            )

        return [WorldEvent(
            event_type=EventType.TRADE_REJECTED,
            tick=tick,
            actor_id=npc.npc_id,
            origin_x=npc.x,
            origin_y=npc.y,
            radius=5,
            payload={"from_id": from_id},
        )]

    def _do_counter_trade(self, npc: NPC, action: dict, world: World, tick: int) -> list[WorldEvent]:
        """Counter a pending proposal with different terms."""
        proposal = self._find_proposal(npc, action)
        if not proposal:
            return []

        from_id = proposal["from_id"]
        from_npc = world.get_npc(from_id)
        npc.pending_proposals.remove(proposal)

        offer_item = action.get("offer_item", "")
        offer_qty = int(action.get("offer_qty", 0) or 0)
        request_item = action.get("request_item", "")
        request_qty = int(action.get("request_qty", 0) or 0)

        if not offer_item or not request_item or offer_qty <= 0 or request_qty <= 0:
            return []

        # Verify counter-proposer has what they're offering
        if npc.inventory.get(offer_item) < offer_qty:
            return []

        npc.last_action = "counter_trade"
        from_name = from_npc.name if from_npc else from_id
        npc.last_action_result = f"向{from_name}反提议：{offer_qty}{offer_item}换{request_qty}{request_item}"

        # Send counter proposal to original proposer
        if from_npc:
            counter = {
                "from_id": npc.npc_id,
                "offer_item": offer_item,
                "offer_qty": offer_qty,
                "request_item": request_item,
                "request_qty": request_qty,
                "tick": tick,
                "round": proposal.get("round", 1) + 1,
            }
            from_npc.pending_proposals.append(counter)

        return [WorldEvent(
            event_type=EventType.TRADE_COUNTERED,
            tick=tick,
            actor_id=npc.npc_id,
            origin_x=npc.x,
            origin_y=npc.y,
            radius=5,
            payload={
                "from_id": from_id,
                "offer_item": offer_item, "offer_qty": offer_qty,
                "request_item": request_item, "request_qty": request_qty,
            },
        )]

    def _do_build(self, character, action: dict, world: World, tick: int) -> list[WorldEvent]:
        """Build furniture on the current tile. Works for NPC or Player."""
        furniture = (action.get("build_furniture") or action.get("furniture_type", "")).strip()
        recipe = config.FURNITURE_RECIPES.get(furniture)
        if not recipe:
            return []

        tile = world.get_tile(character.x, character.y)
        if not tile or tile.furniture:
            return []  # tile already has furniture

        # Check materials
        for mat, qty in recipe.items():
            if character.inventory.get(mat) < qty:
                return []

        # Consume materials and place furniture
        for mat, qty in recipe.items():
            character.inventory.set(mat, character.inventory.get(mat) - qty)
        tile.furniture = furniture

        actor_id = getattr(character, "npc_id", getattr(character, "player_id", "unknown"))
        character.last_action = "build"
        character.last_action_result = f"在({character.x},{character.y})建造了{furniture}"

        return [WorldEvent(
            event_type=EventType.FURNITURE_BUILT,
            tick=tick,
            actor_id=actor_id,
            origin_x=character.x,
            origin_y=character.y,
            radius=4,
            payload={"furniture": furniture, "x": character.x, "y": character.y},
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
        elif action_type == "craft":
            events.extend(self._do_craft(player, action, world, tick))
        elif action_type == "sell":
            events.extend(self._do_sell(player, action, world, tick))
        elif action_type == "buy":
            events.extend(self._do_buy(player, action, world, tick))
        elif action_type == "use_item":
            events.extend(self._player_use_item(player, action, world, tick))
        elif action_type == "build":
            events.extend(self._do_build(player, action, world, tick))
        elif action_type == "propose_trade":
            events.extend(self._player_propose_trade(player, action, world, tick))
        elif action_type == "accept_trade":
            events.extend(self._player_accept_trade(player, action, world, tick))
        elif action_type == "reject_trade":
            events.extend(self._player_reject_trade(player, action, world, tick))
        elif action_type == "dialogue_reply":
            events.extend(self._player_dialogue_reply(player, action, world, tick))
        elif action_type == "rest":
            tile = world.get_tile(player.x, player.y)
            rest_energy = 20
            if tile and tile.furniture == "chair":
                rest_energy = config.FURNITURE_EFFECTS.get("chair", {}).get("rest_energy", 35)
            player.energy = min(100, player.energy + rest_energy)
        elif action_type == "sleep":
            tile = world.get_tile(player.x, player.y)
            if tile and tile.furniture == "bed":
                restore = config.FURNITURE_EFFECTS.get("bed", {}).get("sleep_energy", config.SLEEP_ENERGY_RESTORE)
            else:
                restore = config.SLEEP_ENERGY_RESTORE
            player.energy = min(100, player.energy + restore)

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
        if player.equipped == "rope":
            rope_save = config.ITEM_EFFECTS.get("rope", {}).get("move_energy_save", 0)
            energy_cost = max(0, energy_cost - rope_save)
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
        base_amount = 2
        if player.equipped == "tool":
            base_amount *= config.ITEM_EFFECTS.get("tool", {}).get("gather_bonus", 1)
        amount = min(base_amount, tile.resource.quantity)

        # Capacity check
        if not player.inventory.has_space(amount):
            amount = config.INVENTORY_MAX_SLOTS - player.inventory.total_items()
        if amount <= 0:
            return []

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

        if not player.inventory.has_space(qty):
            qty = config.INVENTORY_MAX_SLOTS - player.inventory.total_items()
            cost = qty * config.FOOD_COST_GOLD
        if qty <= 0:
            return []

        player.inventory.gold -= cost
        player.inventory.food += qty
        return []

    def _player_use_item(self, player: Player, action: dict, world: World, tick: int) -> list[WorldEvent]:
        item = action.get("use_item", "").strip()
        if not item or player.inventory.get(item) <= 0:
            return []

        effects = config.ITEM_EFFECTS.get(item, {})

        if "energy" in effects:
            restore = effects["energy"]
            player.energy = min(100, player.energy + restore)
            player.inventory.set(item, player.inventory.get(item) - 1)
            return [WorldEvent(
                event_type=EventType.PLAYER_USED_ITEM,
                tick=tick,
                actor_id="player",
                origin_x=player.x,
                origin_y=player.y,
                radius=2,
                payload={"item": item, "effect": f"恢复{restore}体力"},
            )]
        elif "gather_bonus" in effects or "move_energy_save" in effects:
            events = self._do_equip_item(player, item, world, tick)
            return events

        return []

    def _player_propose_trade(self, player: Player, action: dict, world: World, tick: int) -> list[WorldEvent]:
        target_id = action.get("target_id", "")
        target_npc = world.get_npc(target_id)
        if not target_npc:
            return []

        dist = abs(target_npc.x - player.x) + abs(target_npc.y - player.y)
        if dist > config.NPC_ADJACENT_RADIUS + 2:
            return []

        offer_item = action.get("offer_item", "")
        offer_qty = int(action.get("offer_qty", 0) or 0)
        request_item = action.get("request_item", "")
        request_qty = int(action.get("request_qty", 0) or 0)

        if not offer_item or not request_item or offer_qty <= 0 or request_qty <= 0:
            return []
        if player.inventory.get(offer_item) < offer_qty:
            return []

        proposal = {
            "from_id": "player",
            "offer_item": offer_item, "offer_qty": offer_qty,
            "request_item": request_item, "request_qty": request_qty,
            "tick": tick, "round": 1,
        }
        target_npc.pending_proposals.append(proposal)
        target_npc.memory.add_to_inbox(
            f"[{player.name}] 向你提出交易提案: {offer_qty}{offer_item}↔{request_qty}{request_item}"
        )
        return [WorldEvent(
            event_type=EventType.TRADE_PROPOSED,
            tick=tick,
            actor_id="player",
            origin_x=player.x,
            origin_y=player.y,
            radius=5,
            payload={"target_id": target_id, "offer_item": offer_item, "offer_qty": offer_qty,
                     "request_item": request_item, "request_qty": request_qty},
        )]

    def _player_accept_trade(self, player: Player, action: dict, world: World, tick: int) -> list[WorldEvent]:
        """Accept a trade proposal from an NPC (player has pending proposals in inbox)."""
        from_id = action.get("proposal_from", "")
        target_npc = world.get_npc(from_id)
        if not target_npc:
            return []

        # Find matching proposal in NPC's pending list directed to player
        proposal = None
        for p in target_npc.pending_proposals:
            if p.get("from_id") == from_id:
                proposal = p
                break

        # Alternatively, treat as direct action: player accepts offer stored in action
        offer_item = action.get("offer_item", "")
        offer_qty = int(action.get("offer_qty", 0) or 0)
        request_item = action.get("request_item", "")
        request_qty = int(action.get("request_qty", 0) or 0)

        if not offer_item or not request_item or offer_qty <= 0 or request_qty <= 0:
            return []

        if (target_npc.inventory.get(offer_item) < offer_qty or
                player.inventory.get(request_item) < request_qty):
            return []

        if not player.inventory.has_space(offer_qty):
            return []

        target_npc.inventory.set(offer_item, target_npc.inventory.get(offer_item) - offer_qty)
        target_npc.inventory.set(request_item, target_npc.inventory.get(request_item) + request_qty)
        player.inventory.set(offer_item, player.inventory.get(offer_item) + offer_qty)
        player.inventory.set(request_item, player.inventory.get(request_item) - request_qty)

        return [WorldEvent(
            event_type=EventType.TRADE_ACCEPTED,
            tick=tick,
            actor_id="player",
            origin_x=player.x,
            origin_y=player.y,
            radius=5,
            payload={"with": from_id, "offer_item": offer_item, "offer_qty": offer_qty,
                     "request_item": request_item, "request_qty": request_qty},
        )]

    def _player_reject_trade(self, player: Player, action: dict, world: World, tick: int) -> list[WorldEvent]:
        from_id = action.get("proposal_from", "")
        target_npc = world.get_npc(from_id)
        if target_npc:
            target_npc.memory.add_to_inbox(f"[{player.name}] 拒绝了你的交易提案")
        return [WorldEvent(
            event_type=EventType.TRADE_REJECTED,
            tick=tick,
            actor_id="player",
            origin_x=player.x,
            origin_y=player.y,
            radius=3,
            payload={"from_id": from_id},
        )]

    def _player_dialogue_reply(self, player: Player, action: dict, world: World, tick: int) -> list[WorldEvent]:
        to_npc_id = action.get("to_npc_id", "")
        reply_msg = str(action.get("message", "")).strip()
        npc = world.get_npc(to_npc_id)
        if npc and reply_msg:
            npc.memory.add_to_inbox(f"[{player.name}] 对你说: {reply_msg}")
        # Remove handled dialogue from queue
        player.dialogue_queue = [
            d for d in player.dialogue_queue if d.get("from_id") != to_npc_id
        ]
        return [WorldEvent(
            event_type=EventType.PLAYER_DIALOGUE_REPLIED,
            tick=tick,
            actor_id="player",
            origin_x=player.x,
            origin_y=player.y,
            radius=5,
            payload={"to_npc_id": to_npc_id, "message": reply_msg},
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
