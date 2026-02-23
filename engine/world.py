"""Core world data models and world generation."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import config


class TileType(str, Enum):
    GRASS = "grass"
    WATER = "water"
    ROCK = "rock"
    FOREST = "forest"


class WeatherType(str, Enum):
    SUNNY = "sunny"
    RAINY = "rainy"
    STORM = "storm"


class ResourceType(str, Enum):
    WOOD = "wood"
    STONE = "stone"
    ORE = "ore"


@dataclass
class Resource:
    resource_type: ResourceType
    quantity: int
    max_quantity: int


@dataclass
class Tile:
    x: int
    y: int
    tile_type: TileType
    resource: Optional[Resource] = None
    npc_ids: list = field(default_factory=list)


@dataclass
class WorldTime:
    tick: int = 0
    hour: float = 6.0
    day: int = 1
    hours_per_tick: float = 0.5   # game hours advanced each world tick

    @property
    def phase(self) -> str:
        h = self.hour
        if 5 <= h < 8:
            return "dawn"
        elif 8 <= h < 18:
            return "day"
        elif 18 <= h < 21:
            return "dusk"
        else:
            return "night"

    @property
    def time_str(self) -> str:
        return f"Day {self.day} {int(self.hour):02d}:{int((self.hour % 1) * 60):02d}"

    def advance(self):
        self.tick += 1
        self.hour += self.hours_per_tick
        if self.hour >= 24.0:
            self.hour -= 24.0
            self.day += 1


@dataclass
class Inventory:
    wood: int = 0
    stone: int = 0
    ore: int = 0

    def get(self, item: str) -> int:
        return getattr(self, item, 0)

    def set(self, item: str, value: int):
        if hasattr(self, item):
            setattr(self, item, max(0, value))


@dataclass
class AgentMemory:
    # List of {"role": "user"/"model", "text": str}
    conversation_history: list = field(default_factory=list)
    personal_notes: list = field(default_factory=list)
    inbox: list = field(default_factory=list)   # events received since last cycle
    max_history_turns: int = config.HISTORY_MAX_TURNS
    max_notes: int = config.NOTES_MAX_COUNT

    def add_history_turn(self, role: str, text: str):
        self.conversation_history.append({"role": role, "text": text})
        # Prune to max_history_turns pairs (2 items = 1 turn)
        max_items = self.max_history_turns * 2
        if len(self.conversation_history) > max_items:
            self.conversation_history = self.conversation_history[-max_items:]

    def add_note(self, note: str):
        self.personal_notes.append(note)
        if len(self.personal_notes) > self.max_notes:
            self.personal_notes.pop(0)

    def clear_inbox(self):
        self.inbox.clear()

    def add_to_inbox(self, event_summary: str):
        self.inbox.append(event_summary)


@dataclass
class NPC:
    npc_id: str
    name: str
    x: int
    y: int
    personality: str
    color: str
    inventory: Inventory = field(default_factory=Inventory)
    memory: AgentMemory = field(default_factory=AgentMemory)
    is_processing: bool = False
    last_action: str = "idle"
    last_message: str = ""
    last_message_tick: int = -99
    energy: int = 100


@dataclass
class GodEntity:
    personality: str = "神秘而公正的神明，默默观察世界，偶尔干预以维持平衡，文字富有诗意"
    memory: AgentMemory = field(default_factory=AgentMemory)
    is_processing: bool = False
    last_commentary: str = "世界在我的注视下缓缓运转..."
    pending_commands: list = field(default_factory=list)  # from browser UI


@dataclass
class World:
    width: int = config.WORLD_WIDTH
    height: int = config.WORLD_HEIGHT
    tiles: list = field(default_factory=list)   # list[list[Tile]]
    weather: WeatherType = WeatherType.SUNNY
    time: WorldTime = field(default_factory=WorldTime)
    npcs: list = field(default_factory=list)    # list[NPC]
    god: GodEntity = field(default_factory=GodEntity)
    recent_events: list = field(default_factory=list)  # global event log (last 30)

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return None

    def get_npc(self, npc_id: str) -> Optional[NPC]:
        return next((n for n in self.npcs if n.npc_id == npc_id), None)

    def get_nearby_npcs(self, npc: NPC, radius: int) -> list:
        return [
            n for n in self.npcs
            if n.npc_id != npc.npc_id
            and abs(n.x - npc.x) + abs(n.y - npc.y) <= radius
        ]

    def add_event(self, summary: str):
        self.recent_events.append(summary)
        if len(self.recent_events) > 30:
            self.recent_events.pop(0)


# ── World generation ──────────────────────────────────────────────────────────

def _place_cluster(tiles, width, height, tile_type: TileType, cx: int, cy: int, radius: int):
    """Place a cluster of the given tile type around (cx, cy)."""
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy <= radius * radius:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < width and 0 <= ny < height:
                    # Don't overwrite water with non-water (keeps shape)
                    if tiles[ny][nx].tile_type == TileType.GRASS:
                        tiles[ny][nx].tile_type = tile_type


def create_world(seed: int = 42) -> World:
    rng = random.Random(seed)
    width, height = config.WORLD_WIDTH, config.WORLD_HEIGHT

    # Initialize all grass
    tiles: list[list[Tile]] = [
        [Tile(x=x, y=y, tile_type=TileType.GRASS) for x in range(width)]
        for y in range(height)
    ]

    # Water: central lake + a winding river
    lake_cx, lake_cy = width // 2, height // 2
    _place_cluster(tiles, width, height, TileType.WATER, lake_cx, lake_cy, 2)
    # Small rivers branching from lake
    for _ in range(3):
        cx, cy = lake_cx, lake_cy
        for _ in range(rng.randint(3, 6)):
            cx += rng.randint(-2, 2)
            cy += rng.randint(-2, 2)
            cx = max(1, min(width - 2, cx))
            cy = max(1, min(height - 2, cy))
            _place_cluster(tiles, width, height, TileType.WATER, cx, cy, 1)

    # Rock clusters (4 patches)
    rock_centers = [(4, 4), (15, 4), (4, 15), (15, 15)]
    for rcx, rcy in rock_centers:
        _place_cluster(tiles, width, height, TileType.ROCK, rcx, rcy, rng.randint(2, 3))

    # Forest patches (scattered)
    for _ in range(6):
        fcx = rng.randint(2, width - 3)
        fcy = rng.randint(2, height - 3)
        _place_cluster(tiles, width, height, TileType.FOREST, fcx, fcy, rng.randint(1, 3))

    # Add resources to tiles
    for row in tiles:
        for tile in row:
            if tile.tile_type == TileType.FOREST:
                if rng.random() < 0.75:
                    qty = rng.randint(4, 10)
                    tile.resource = Resource(ResourceType.WOOD, qty, 10)
            elif tile.tile_type == TileType.ROCK:
                if rng.random() < 0.65:
                    if rng.random() < 0.3:
                        qty = rng.randint(1, 5)
                        tile.resource = Resource(ResourceType.ORE, qty, 5)
                    else:
                        qty = rng.randint(4, 10)
                        tile.resource = Resource(ResourceType.STONE, qty, 10)

    # Ensure NPC spawn points are on grass
    spawn_points = [(3, 3), (16, 3), (3, 16), (16, 16)]
    for sx, sy in spawn_points:
        tiles[sy][sx].tile_type = TileType.GRASS
        tiles[sy][sx].resource = None

    # Create NPCs
    npcs = [
        NPC(
            npc_id="npc_alice",
            name="Alice",
            x=3, y=3,
            personality="好奇心旺盛，喜欢探索和收集矿石，话多且友善，总是充满热情",
            color="#4CAF50",
        ),
        NPC(
            npc_id="npc_bob",
            name="Bob",
            x=16, y=3,
            personality="沉稳可靠，擅长采集木材，是个精明的交易者，说话简洁",
            color="#2196F3",
        ),
        NPC(
            npc_id="npc_carol",
            name="Carol",
            x=3, y=16,
            personality="聪明机智，善于观察和分析，喜欢策略，偶尔有点神秘",
            color="#FFC107",
        ),
        NPC(
            npc_id="npc_dave",
            name="Dave",
            x=16, y=16,
            personality="勤劳踏实，专注采集石头，效率极高，话不多但行动力强",
            color="#F44336",
        ),
    ]

    # Register NPC positions on tiles
    for npc in npcs:
        tile = tiles[npc.y][npc.x]
        tile.npc_ids.append(npc.npc_id)

    return World(
        width=width,
        height=height,
        tiles=tiles,
        npcs=npcs,
        god=GodEntity(),
    )
