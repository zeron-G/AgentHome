extends Node
## Global state singleton (Autoload). Caches parsed world_state from server.

# Connection
var server_url: String = "ws://localhost:8000/ws"

# Raw data
var world_data: Dictionary = {}
var simulation_running: bool = false

# Parsed state
var player: Dictionary = {}
var npcs: Array = []
var events: Array = []
var god_commentary: String = ""
var current_tick: int = 0
var time_data: Dictionary = {}
var weather: String = "sunny"
var tiles: Array = []
var market: Dictionary = {}
var token_usage: Dictionary = {}
var settings: Dictionary = {}

# Narrative / season state
var season: String = "spring"
var season_name: String = "春·播种"
var narrative_stage: int = 0
var god_season: String = "spring"

# Signals
signal world_state_updated
signal season_changed(new_season: String)
signal dialogue_received(dialogue: Dictionary)
signal dialogue_cleared
signal connection_status_changed(is_connected: bool)
signal event_received(event: Dictionary)
signal settings_updated(new_settings: Dictionary)
signal market_updated(new_market: Dictionary)
signal token_updated(new_usage: Dictionary)

# ── Constants ──

const CRAFTING_RECIPES := {
	"rope":   {"wood": 2},
	"potion": {"herb": 2},
	"tool":   {"stone": 1, "wood": 1},
	"bread":  {"food": 2},
}

const ITEM_EFFECTS := {
	"potion": {"type": "consume", "energy": 60},
	"bread":  {"type": "consume", "energy": 50},
	"tool":   {"type": "equip", "effect": "采集×2"},
	"rope":   {"type": "equip", "effect": "移动消耗-1"},
}

const FURNITURE_RECIPES := {
	"bed":   {"wood": 4, "effect": "睡觉恢复+80"},
	"table": {"wood": 3, "effect": "合成产出×2"},
	"chair": {"wood": 2, "effect": "休息恢复+35"},
}

const ITEM_NAMES := {
	"wood": "木头", "stone": "石头", "ore": "矿石",
	"food": "食物", "herb": "草药",
	"rope": "绳子", "potion": "药水", "tool": "工具", "bread": "面包",
}

const WEATHER_NAMES := {"sunny": "晴天", "rainy": "雨天", "storm": "暴风雨"}
const PHASE_NAMES := {"dawn": "晨", "day": "日", "dusk": "昏", "night": "夜"}

const EVENT_COLORS := {
	"npc_spoke": "#4ecca3", "player_spoke": "#4ecca3", "player_dialogue_replied": "#4ecca3",
	"npc_traded": "#f5a623", "trade_accepted": "#f5a623",
	"npc_sold": "#f5a623", "npc_bought": "#f5a623",
	"player_sold": "#f5a623", "player_bought": "#f5a623",
	"npc_gathered": "#8bc34a", "player_gathered": "#8bc34a",
	"npc_crafted": "#00bcd4", "player_crafted": "#00bcd4",
	"npc_equipped": "#00bcd4", "player_equipped": "#00bcd4",
	"furniture_built": "#00bcd4",
	"weather_changed": "#aa88ff",
	"market_updated": "#2196f3",
	"god_commentary": "#9c27b0",
}


func update_from_server(data: Dictionary) -> void:
	world_data = data
	current_tick = data.get("tick", 0)
	simulation_running = data.get("simulation_running", false)
	time_data = data.get("time", {})
	weather = data.get("weather", "sunny")

	# Season tracking
	var new_season = time_data.get("season", "spring")
	if new_season != season:
		season = new_season
		season_name = time_data.get("season_name", "")
		season_changed.emit(season)
	else:
		season_name = time_data.get("season_name", season_name)
	npcs = data.get("npcs", [])
	player = data.get("player", {})
	tiles = data.get("tiles", [])

	# Market
	var new_market = data.get("market", {})
	if new_market != market:
		market = new_market
		market_updated.emit(market)

	# Token usage
	var new_usage = data.get("token_usage", {})
	if new_usage != token_usage:
		token_usage = new_usage
		token_updated.emit(token_usage)

	# Settings
	var new_settings = data.get("settings", {})
	if new_settings != settings:
		settings = new_settings
		settings_updated.emit(settings)

	# God commentary & narrative state
	var god_data = data.get("god", {})
	if god_data is Dictionary:
		god_commentary = god_data.get("commentary", "")
		narrative_stage = god_data.get("narrative_stage", narrative_stage)
		god_season = god_data.get("season", god_season)
	else:
		god_commentary = ""

	# Process events
	var new_events = data.get("events", [])
	for evt in new_events:
		if evt is Dictionary:
			event_received.emit(evt)
	events = new_events

	# Check dialogue
	if not player.is_empty() and player.has("dialogue") and player["dialogue"] != null:
		var dlg = player["dialogue"]
		if dlg is Dictionary and not dlg.is_empty():
			dialogue_received.emit(dlg)
		else:
			dialogue_cleared.emit()
	else:
		dialogue_cleared.emit()

	world_state_updated.emit()


## Check if player is on an exchange tile.
func is_player_at_exchange() -> bool:
	if player.is_empty():
		return false
	var px: int = player.get("x", -1)
	var py: int = player.get("y", -1)
	for tile in tiles:
		if tile is Dictionary and tile.get("x", -1) == px and tile.get("y", -1) == py:
			return tile.get("e", 0) == 1
	return false


## Get player inventory as Dictionary.
func get_player_inventory() -> Dictionary:
	if player.is_empty():
		return {}
	return player.get("inventory", {})


## Check if player can craft a specific item.
func can_craft(item: String) -> bool:
	if not CRAFTING_RECIPES.has(item):
		return false
	var inv := get_player_inventory()
	for mat in CRAFTING_RECIPES[item]:
		if int(inv.get(mat, 0)) < CRAFTING_RECIPES[item][mat]:
			return false
	return true
