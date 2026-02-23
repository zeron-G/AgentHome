import os
from dotenv import load_dotenv

load_dotenv()

# LLM provider: "gemini" (cloud) or "local" (OpenAI-compatible local server)
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")

# Gemini (cloud)
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Local LLM (Ollama / LM Studio / llama.cpp / vLLM / any OpenAI-compatible server)
LOCAL_LLM_BASE_URL: str = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
LOCAL_LLM_MODEL: str = os.getenv("LOCAL_LLM_MODEL", "llama3")

# World
WORLD_WIDTH: int = 20
WORLD_HEIGHT: int = 20

# Timing (seconds) — all hot-modifiable via settings panel
WORLD_TICK_SECONDS: float = float(os.getenv("WORLD_TICK_SECONDS", "3.0"))
NPC_MIN_THINK_SECONDS: float = float(os.getenv("NPC_MIN_THINK_SECONDS", "5.0"))
NPC_MAX_THINK_SECONDS: float = float(os.getenv("NPC_MAX_THINK_SECONDS", "10.0"))
GOD_MIN_THINK_SECONDS: float = float(os.getenv("GOD_MIN_THINK_SECONDS", "20.0"))
GOD_MAX_THINK_SECONDS: float = float(os.getenv("GOD_MAX_THINK_SECONDS", "40.0"))

# Agent memory
HISTORY_MAX_TURNS: int = 20   # max conversation history turns per NPC
NOTES_MAX_COUNT: int = 10     # max personal notes per NPC

# NPC perception — hot-modifiable
NPC_HEARING_RADIUS: int = int(os.getenv("NPC_HEARING_RADIUS", "5"))
NPC_ADJACENT_RADIUS: int = 1  # for trade/interact
NPC_VISION_RADIUS: int = 2    # tiles each direction → 5×5 visible area

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

# Exchange rates (resources → gold) — hot-modifiable
EXCHANGE_RATE_WOOD: int = 1    # 1 gold per wood
EXCHANGE_RATE_STONE: int = 2   # 2 gold per stone
EXCHANGE_RATE_ORE: int = 5     # 5 gold per ore
FOOD_COST_GOLD: int = 3        # 3 gold per food purchased

# Energy restoration — hot-modifiable
FOOD_ENERGY_RESTORE: int = 30  # energy restored by eating 1 food
SLEEP_ENERGY_RESTORE: int = 50 # energy restored by sleeping

# ── New feature flags ────────────────────────────────────────────────────────

# Simulation starts paused — agents won't run until player clicks "Start"
SIMULATION_AUTO_START: bool = False

# NPC thought visibility — hot-modifiable via settings
SHOW_NPC_THOUGHTS: bool = True

# Player character
PLAYER_ENABLED: bool = True
PLAYER_NAME: str = os.getenv("PLAYER_NAME", "玩家")
PLAYER_START_X: int = 12
PLAYER_START_Y: int = 12

# RAG / memory persistence
RAG_ENABLED: bool = True
RAG_SAVE_DIR: str = os.getenv("RAG_SAVE_DIR", "saves")
RAG_MAX_MEMORIES_PER_NPC: int = 200   # max stored memory records per NPC
RAG_SEARCH_LIMIT: int = 5             # records injected into NPC context per cycle
