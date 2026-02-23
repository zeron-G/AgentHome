"""World event system: event types, WorldEvent dataclass, EventBus."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional

import config

if TYPE_CHECKING:
    from engine.world import NPC, World


class EventType(str, Enum):
    NPC_SPOKE = "npc_spoke"
    NPC_MOVED = "npc_moved"
    NPC_GATHERED = "npc_gathered"
    NPC_TRADED = "npc_traded"
    NPC_RESTED = "npc_rested"
    NPC_THOUGHT = "npc_thought"
    WEATHER_CHANGED = "weather_changed"
    RESOURCE_SPAWNED = "resource_spawned"
    RESOURCE_DEPLETED = "resource_depleted"
    TIME_ADVANCED = "time_advanced"
    GOD_COMMENTARY = "god_commentary"


@dataclass
class WorldEvent:
    event_type: EventType
    tick: int
    actor_id: Optional[str] = None
    origin_x: Optional[int] = None
    origin_y: Optional[int] = None
    radius: int = config.NPC_HEARING_RADIUS
    payload: dict = field(default_factory=dict)

    def to_summary(self, world: "World") -> str:
        """Convert event to a readable string for NPC inbox/context."""
        actor_name = ""
        if self.actor_id:
            npc = world.get_npc(self.actor_id)
            actor_name = npc.name if npc else self.actor_id

        et = self.event_type
        p = self.payload

        if et == EventType.NPC_SPOKE:
            target = p.get("target_id")
            target_name = ""
            if target:
                tn = world.get_npc(target)
                target_name = f" (对{tn.name}说)" if tn else ""
            return f"{actor_name}{target_name}: \"{p.get('message', '')}\""

        elif et == EventType.NPC_MOVED:
            return f"{actor_name} 移动到 ({self.origin_x},{self.origin_y})"

        elif et == EventType.NPC_GATHERED:
            return f"{actor_name} 采集了 {p.get('amount',0)} {p.get('resource','?')}"

        elif et == EventType.NPC_TRADED:
            with_name = ""
            wid = p.get("with")
            if wid:
                wn = world.get_npc(wid)
                with_name = wn.name if wn else wid
            return (f"{actor_name} 与 {with_name} 交易: "
                    f"给出 {p.get('offer_qty',0)}{p.get('offer_item','?')}, "
                    f"换取 {p.get('request_qty',0)}{p.get('request_item','?')}")

        elif et == EventType.WEATHER_CHANGED:
            return f"天气变为 {p.get('weather','?')}"

        elif et == EventType.RESOURCE_SPAWNED:
            return f"上帝在({p.get('x','?')},{p.get('y','?')})刷新了 {p.get('resource_type','?')}"

        elif et == EventType.RESOURCE_DEPLETED:
            return f"({self.origin_x},{self.origin_y}) 的资源已耗尽"

        elif et == EventType.GOD_COMMENTARY:
            return f"[上帝旁白] {p.get('commentary','')}"

        return str(et)

    def to_dict(self, world: "World") -> dict:
        """Convert to JSON-serializable dict for WebSocket broadcast."""
        d = {
            "type": self.event_type.value,
            "tick": self.tick,
            "actor": None,
            "summary": self.to_summary(world),
        }
        if self.actor_id:
            npc = world.get_npc(self.actor_id)
            d["actor"] = npc.name if npc else self.actor_id
        d.update(self.payload)
        return d


class EventBus:
    """Dispatches events to nearby NPC inboxes and the global event log."""

    def dispatch(self, event: WorldEvent, world: "World"):
        summary = event.to_summary(world)
        world.add_event(summary)

        # Route to NPC inboxes based on proximity
        for npc in world.npcs:
            if npc.npc_id == event.actor_id:
                continue  # actor doesn't receive their own event in inbox
            if event.origin_x is None:
                # Global event (weather, god action)
                npc.memory.add_to_inbox(summary)
            else:
                dist = abs(npc.x - event.origin_x) + abs(npc.y - event.origin_y)
                if dist <= event.radius:
                    npc.memory.add_to_inbox(summary)
