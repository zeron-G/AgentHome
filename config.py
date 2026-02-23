import os
from dotenv import load_dotenv

load_dotenv()

# LLM
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

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
