import os
from dotenv import load_dotenv

load_dotenv()

# LLM
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# World
WORLD_WIDTH: int = 20
WORLD_HEIGHT: int = 20

# Timing (seconds)
WORLD_TICK_SECONDS: float = 3.0       # world time/passive effects update
NPC_MIN_THINK_SECONDS: float = 5.0    # min wait between NPC decisions
NPC_MAX_THINK_SECONDS: float = 10.0   # max wait between NPC decisions
GOD_MIN_THINK_SECONDS: float = 20.0
GOD_MAX_THINK_SECONDS: float = 40.0

# Agent memory
HISTORY_MAX_TURNS: int = 20   # max conversation history turns per NPC
NOTES_MAX_COUNT: int = 10     # max personal notes per NPC

# NPC perception
NPC_HEARING_RADIUS: int = 5   # tiles, Manhattan distance
NPC_ADJACENT_RADIUS: int = 1  # for trade/interact

# Token tracking
DEFAULT_TOKEN_LIMIT: int = 200_000

# LLM generation
LLM_TEMPERATURE: float = 0.85
LLM_MAX_TOKENS: int = 1024

# Town & Exchange
TOWN_X: int = 9            # town area top-left corner X
TOWN_Y: int = 9            # town area top-left corner Y
EXCHANGE_X: int = 10       # exchange building tile X
EXCHANGE_Y: int = 10       # exchange building tile Y

# Exchange rates (resources → gold)
EXCHANGE_RATE_WOOD: int = 1    # 1 gold per wood
EXCHANGE_RATE_STONE: int = 2   # 2 gold per stone
EXCHANGE_RATE_ORE: int = 5     # 5 gold per ore
FOOD_COST_GOLD: int = 3        # 3 gold per food purchased

# Energy restoration
FOOD_ENERGY_RESTORE: int = 30  # energy restored by eating 1 food
SLEEP_ENERGY_RESTORE: int = 50 # energy restored by sleeping
