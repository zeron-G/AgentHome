class_name HeaderBar
extends HBoxContainer
## Top header bar: time, season, weather, token usage, connection status,
## last action result, simulation control, and home button.
## Dark tarot theme — inherits UIManager theme; only layout & icons set here.

signal simulation_toggled
signal home_pressed

# ── Node refs ──
var _time_label: Label
var _weather_icon: TextureRect
var _weather_label: Label
var _season_icon: TextureRect
var _season_label: Label
var _token_bar: ProgressBar
var _token_label: Label
var _conn_dot: ColorRect
var _conn_label: Label
var _status_label: Label
var _sim_button: Button
var _home_button: Button

# Season icon map
const SEASON_ICONS := {
	"spring": "res://resources/art/ui/season_spring.png",
	"summer": "res://resources/art/ui/season_summer.png",
	"autumn": "res://resources/art/ui/season_autumn.png",
	"winter": "res://resources/art/ui/season_winter.png",
}

# Weather icon text fallback (loaded from art if available)
const WEATHER_ICON_MAP := {
	"sunny": "☀",
	"rainy": "🌧",
	"storm": "⛈",
}


func _ready() -> void:
	custom_minimum_size.y = 38
	add_theme_constant_override("separation", 10)

	# ── Season badge ──
	var season_box := HBoxContainer.new()
	season_box.add_theme_constant_override("separation", 4)
	add_child(season_box)

	_season_icon = TextureRect.new()
	_season_icon.custom_minimum_size = Vector2(20, 20)
	_season_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_season_icon.expand_mode = TextureRect.EXPAND_FIT_WIDTH_PROPORTIONAL
	season_box.add_child(_season_icon)

	_season_label = Label.new()
	_season_label.text = "春·播种"
	_season_label.add_theme_color_override("font_color", Color("#c8a832"))
	_season_label.add_theme_font_size_override("font_size", 13)
	season_box.add_child(_season_label)

	add_child(_make_vsep())

	# ── Time ──
	_time_label = Label.new()
	_time_label.text = "Day 1 06:00  晨"
	add_child(_time_label)

	add_child(_make_vsep())

	# ── Weather ──
	var weather_box := HBoxContainer.new()
	weather_box.add_theme_constant_override("separation", 4)
	add_child(weather_box)

	_weather_icon = TextureRect.new()
	_weather_icon.custom_minimum_size = Vector2(18, 18)
	_weather_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_weather_icon.expand_mode = TextureRect.EXPAND_FIT_WIDTH_PROPORTIONAL
	_weather_icon.visible = false
	weather_box.add_child(_weather_icon)

	_weather_label = Label.new()
	_weather_label.text = "晴天"
	weather_box.add_child(_weather_label)

	add_child(_make_vsep())

	# ── Token usage ──
	var token_box := HBoxContainer.new()
	token_box.add_theme_constant_override("separation", 4)
	add_child(token_box)

	var token_icon := Label.new()
	token_icon.text = "Token:"
	token_icon.add_theme_color_override("font_color", Color("#8888a0"))
	token_icon.add_theme_font_size_override("font_size", 12)
	token_box.add_child(token_icon)

	_token_bar = ProgressBar.new()
	_token_bar.custom_minimum_size = Vector2(120, 16)
	_token_bar.max_value = 100
	_token_bar.value = 0
	_token_bar.show_percentage = false
	token_box.add_child(_token_bar)

	_token_label = Label.new()
	_token_label.text = "0 / 0"
	_token_label.add_theme_font_size_override("font_size", 12)
	_token_label.add_theme_color_override("font_color", Color("#8888a0"))
	token_box.add_child(_token_label)

	add_child(_make_vsep())

	# ── Last action status line ──
	_status_label = Label.new()
	_status_label.text = ""
	_status_label.add_theme_font_size_override("font_size", 12)
	_status_label.add_theme_color_override("font_color", Color("#8888a0"))
	_status_label.clip_text = true
	_status_label.custom_minimum_size.x = 100
	_status_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	add_child(_status_label)

	# ── Spacer ──
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	add_child(spacer)

	# ── Connection indicator (dot + label) ──
	var conn_box := HBoxContainer.new()
	conn_box.add_theme_constant_override("separation", 4)
	add_child(conn_box)

	# Small colored circle
	_conn_dot = ColorRect.new()
	_conn_dot.custom_minimum_size = Vector2(10, 10)
	_conn_dot.color = Color("#e94560")  # red = disconnected initially
	# Center the dot vertically
	var dot_center := CenterContainer.new()
	dot_center.add_child(_conn_dot)
	conn_box.add_child(dot_center)

	_conn_label = Label.new()
	_conn_label.text = "连接中..."
	_conn_label.add_theme_font_size_override("font_size", 12)
	_conn_label.add_theme_color_override("font_color", Color("#e94560"))
	conn_box.add_child(_conn_label)

	add_child(_make_vsep())

	# ── Simulation button ──
	_sim_button = Button.new()
	_sim_button.text = "开始"
	_sim_button.custom_minimum_size.x = 56
	_sim_button.pressed.connect(func(): simulation_toggled.emit())
	add_child(_sim_button)

	# ── Home button ──
	_home_button = Button.new()
	_home_button.text = "主菜单"
	_home_button.pressed.connect(func(): home_pressed.emit())
	add_child(_home_button)

	# Load initial season icon
	_load_season_icon(GameState.season)


# ── Public API (kept compatible) ──

func update_time(time_data: Dictionary, weather: String) -> void:
	var phase_name: String = GameState.PHASE_NAMES.get(time_data.get("phase", ""), "")
	_time_label.text = "%s  %s" % [time_data.get("time_str", ""), phase_name]

	# Weather label
	_weather_label.text = GameState.WEATHER_NAMES.get(weather, weather)

	# Season from time_data (if present)
	var s: String = time_data.get("season", "")
	var sn: String = time_data.get("season_name", "")
	if not s.is_empty():
		update_season(s, sn)

	# Last action result from player data
	var last_action: String = GameState.player.get("last_action_result", "")
	if not last_action.is_empty():
		_status_label.text = last_action
		_status_label.tooltip_text = last_action


func update_token(usage: Dictionary) -> void:
	var used: int = usage.get("total_tokens_used", 0)
	var limit: int = usage.get("limit", 1)
	if limit <= 0:
		limit = 1
	var pct: float = float(used) / float(limit) * 100.0
	_token_bar.value = pct
	_token_label.text = "%s / %s" % [_format_number(used), _format_number(limit)]

	if pct > 80:
		_token_bar.modulate = Color("#e94560")
	elif pct > 60:
		_token_bar.modulate = Color("#f5a623")
	else:
		_token_bar.modulate = Color("#4ecca3")


func update_simulation(running: bool) -> void:
	_sim_button.text = "暂停" if running else "开始"


func set_connected(connected: bool) -> void:
	if connected:
		_conn_dot.color = Color("#4ecca3")
		_conn_label.text = "已连接"
		_conn_label.add_theme_color_override("font_color", Color("#4ecca3"))
	else:
		_conn_dot.color = Color("#e94560")
		_conn_label.text = "断开"
		_conn_label.add_theme_color_override("font_color", Color("#e94560"))


## New: update season badge icon and label text.
func update_season(season: String, season_name: String) -> void:
	_load_season_icon(season)
	if not season_name.is_empty():
		_season_label.text = season_name
	else:
		# Fallback names
		var fallback := {"spring": "春", "summer": "夏", "autumn": "秋", "winter": "冬"}
		_season_label.text = fallback.get(season, season)


# ── Internals ──

func _load_season_icon(season: String) -> void:
	var path: String = SEASON_ICONS.get(season, "")
	if path.is_empty():
		_season_icon.visible = false
		return
	if ResourceLoader.exists(path):
		_season_icon.texture = load(path)
		_season_icon.visible = true
	else:
		_season_icon.visible = false


func _make_vsep() -> VSeparator:
	return VSeparator.new()


static func _format_number(n: int) -> String:
	if n >= 1_000_000:
		return "%.1fM" % (float(n) / 1_000_000.0)
	elif n >= 1_000:
		return "%.0fk" % (float(n) / 1_000.0)
	return str(n)
