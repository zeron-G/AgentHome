class_name SettingsPanel
extends ScrollContainer
## Settings panel: LLM config (Claude/Gemini/Local), game speed, NPC params,
## display, audio, network, energy, exchange rates, world controls, danger zone.
## Each section is collapsible with accent gold headers.

signal control_requested(msg: Dictionary)
signal go_home

var _content: VBoxContainer

# ── LLM ──
var _provider_claude: Button
var _provider_gemini: Button
var _provider_local: Button
var _claude_fields: VBoxContainer
var _claude_api_key_input: LineEdit
var _claude_model_input: LineEdit
var _api_key_input: LineEdit
var _model_input: LineEdit
var _gemini_fields: VBoxContainer
var _local_fields: VBoxContainer
var _local_url_input: LineEdit
var _local_model_input: LineEdit

# ── Speed ──
var _tick_slider: HSlider
var _tick_label: Label
var _npc_min_slider: HSlider
var _npc_min_label: Label
var _npc_max_slider: HSlider
var _npc_max_label: Label

# ── NPC params ──
var _vision_slider: HSlider
var _vision_label: Label
var _hearing_slider: HSlider
var _hearing_label: Label
var _thoughts_check: CheckButton

# ── Display ──
var _window_mode_select: OptionButton
var _ui_scale_slider: HSlider
var _ui_scale_label: Label
var _vsync_check: CheckButton

# ── Audio ──
var _master_vol_slider: HSlider
var _master_vol_label: Label
var _music_vol_slider: HSlider
var _music_vol_label: Label
var _sfx_vol_slider: HSlider
var _sfx_vol_label: Label
var _mute_check: CheckButton

# ── Network ──
var _server_url_input: LineEdit
var _auto_reconnect_check: CheckButton
var _reconnect_delay_slider: HSlider
var _reconnect_delay_label: Label

# ── Energy restoration ──
var _food_energy_slider: HSlider
var _food_energy_label: Label
var _sleep_energy_slider: HSlider
var _sleep_energy_label: Label

# ── Exchange rates ──
var _wood_rate_slider: HSlider
var _wood_rate_label: Label
var _stone_rate_slider: HSlider
var _stone_rate_label: Label
var _ore_rate_slider: HSlider
var _ore_rate_label: Label
var _food_cost_slider: HSlider
var _food_cost_label: Label

# ── Weather ──
var _weather_buttons: Dictionary = {}

# ── Resource spawn ──
var _spawn_type: OptionButton
var _spawn_qty: SpinBox
var _spawn_x: SpinBox
var _spawn_y: SpinBox

# Section visibility tracking
var _section_bodies: Dictionary = {}


func _ready() -> void:
	size_flags_vertical = Control.SIZE_EXPAND_FILL
	size_flags_horizontal = Control.SIZE_EXPAND_FILL

	_content = VBoxContainer.new()
	_content.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_content.add_theme_constant_override("separation", 4)
	add_child(_content)

	_build_llm_section()
	_build_speed_section()
	_build_npc_params_section()
	_build_display_section()
	_build_audio_section()
	_build_network_section()
	_build_energy_section()
	_build_exchange_section()
	_build_controls_section()
	_build_danger_section()


func update_settings(settings: Dictionary) -> void:
	# Speed
	_tick_slider.value = settings.get("world_tick_seconds", 3.0)
	_tick_label.text = "%.1fs" % _tick_slider.value
	_npc_min_slider.value = settings.get("npc_min_think", 5.0)
	_npc_min_label.text = "%.0fs" % _npc_min_slider.value
	_npc_max_slider.value = settings.get("npc_max_think", 10.0)
	_npc_max_label.text = "%.0fs" % _npc_max_slider.value

	# NPC params
	_vision_slider.value = settings.get("npc_vision_radius", 2)
	_vision_label.text = str(int(_vision_slider.value))
	_hearing_slider.value = settings.get("npc_hearing_radius", 5)
	_hearing_label.text = str(int(_hearing_slider.value))
	_thoughts_check.button_pressed = settings.get("show_npc_thoughts", true)

	# Energy restoration
	_food_energy_slider.value = settings.get("food_energy_restore", 30)
	_food_energy_label.text = "%d" % int(_food_energy_slider.value)
	_sleep_energy_slider.value = settings.get("sleep_energy_restore", 50)
	_sleep_energy_label.text = "%d" % int(_sleep_energy_slider.value)

	# Exchange rates
	_wood_rate_slider.value = settings.get("wood_rate", 3.0)
	_wood_rate_label.text = "%.1f" % _wood_rate_slider.value
	_stone_rate_slider.value = settings.get("stone_rate", 4.0)
	_stone_rate_label.text = "%.1f" % _stone_rate_slider.value
	_ore_rate_slider.value = settings.get("ore_rate", 6.0)
	_ore_rate_label.text = "%.1f" % _ore_rate_slider.value
	_food_cost_slider.value = settings.get("food_cost_gold", 2.0)
	_food_cost_label.text = "%.1f" % _food_cost_slider.value

	# Load display/audio/network from SettingsManager
	_load_local_settings()


# ── Section builder helpers ──

func _make_section_header(title_text: String) -> Button:
	var btn := Button.new()
	btn.text = "▼  %s" % title_text
	btn.add_theme_font_size_override("font_size", 14)
	btn.add_theme_color_override("font_color", Color("#c8a832"))
	btn.alignment = HORIZONTAL_ALIGNMENT_LEFT
	# Flat style
	var flat_style := StyleBoxFlat.new()
	flat_style.bg_color = Color("#0a0a14")
	flat_style.border_color = Color("#2a2a3e")
	flat_style.border_width_bottom = 1
	flat_style.content_margin_left = 4
	flat_style.content_margin_top = 4
	flat_style.content_margin_bottom = 4
	btn.add_theme_stylebox_override("normal", flat_style)
	var hover_style := flat_style.duplicate()
	hover_style.bg_color = Color("#1a1a2e")
	btn.add_theme_stylebox_override("hover", hover_style)
	btn.add_theme_stylebox_override("pressed", hover_style)
	return btn


func _make_collapsible_section(title_text: String) -> VBoxContainer:
	var header := _make_section_header(title_text)
	_content.add_child(header)

	var body := VBoxContainer.new()
	body.add_theme_constant_override("separation", 4)
	body.visible = true
	_content.add_child(body)

	_section_bodies[title_text] = body

	header.pressed.connect(func():
		body.visible = not body.visible
		if body.visible:
			header.text = "▼  %s" % title_text
		else:
			header.text = "▶  %s" % title_text
	)

	return body


func _make_slider_row(parent: Control, label_text: String,
		min_v: float, max_v: float, step_v: float, default_v: float,
		value_label_width: int = 40) -> Array:
	## Returns [HSlider, Label]
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 4)
	parent.add_child(row)

	row.add_child(_make_label(label_text))

	var slider := HSlider.new()
	slider.min_value = min_v
	slider.max_value = max_v
	slider.step = step_v
	slider.value = default_v
	slider.custom_minimum_size.x = 120
	slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(slider)

	var val_label := Label.new()
	val_label.custom_minimum_size.x = value_label_width
	val_label.add_theme_font_size_override("font_size", 12)
	row.add_child(val_label)

	return [slider, val_label]


# ── LLM Config ──

func _build_llm_section() -> void:
	var body := _make_collapsible_section("LLM 配置")

	# Provider toggle row
	var provider_row := HBoxContainer.new()
	provider_row.add_theme_constant_override("separation", 4)
	body.add_child(provider_row)

	_provider_claude = Button.new()
	_provider_claude.text = "Claude"
	_provider_claude.toggle_mode = true
	_provider_claude.pressed.connect(func(): _switch_provider("claude"))
	provider_row.add_child(_provider_claude)

	_provider_gemini = Button.new()
	_provider_gemini.text = "Gemini"
	_provider_gemini.toggle_mode = true
	_provider_gemini.button_pressed = true
	_provider_gemini.pressed.connect(func(): _switch_provider("gemini"))
	provider_row.add_child(_provider_gemini)

	_provider_local = Button.new()
	_provider_local.text = "Local LLM"
	_provider_local.toggle_mode = true
	_provider_local.pressed.connect(func(): _switch_provider("local"))
	provider_row.add_child(_provider_local)

	# ── Claude fields ──
	_claude_fields = VBoxContainer.new()
	_claude_fields.visible = false
	_claude_fields.add_theme_constant_override("separation", 4)
	body.add_child(_claude_fields)

	_claude_fields.add_child(_make_label("Anthropic API Key:"))
	_claude_api_key_input = LineEdit.new()
	_claude_api_key_input.secret = true
	_claude_api_key_input.placeholder_text = "输入 Anthropic API Key (sk-ant-...)"
	_claude_fields.add_child(_claude_api_key_input)

	_claude_fields.add_child(_make_label("模型:"))
	_claude_model_input = LineEdit.new()
	_claude_model_input.placeholder_text = "claude-sonnet-4-20250514"
	_claude_fields.add_child(_claude_model_input)

	# ── Gemini fields ──
	_gemini_fields = VBoxContainer.new()
	_gemini_fields.add_theme_constant_override("separation", 4)
	body.add_child(_gemini_fields)

	_gemini_fields.add_child(_make_label("API Key:"))
	_api_key_input = LineEdit.new()
	_api_key_input.secret = true
	_api_key_input.placeholder_text = "输入 Gemini API Key"
	_gemini_fields.add_child(_api_key_input)

	_gemini_fields.add_child(_make_label("模型:"))
	_model_input = LineEdit.new()
	_model_input.placeholder_text = "gemini-2.0-flash"
	_gemini_fields.add_child(_model_input)

	# ── Local fields ──
	_local_fields = VBoxContainer.new()
	_local_fields.visible = false
	_local_fields.add_theme_constant_override("separation", 4)
	body.add_child(_local_fields)

	_local_fields.add_child(_make_label("Base URL:"))
	_local_url_input = LineEdit.new()
	_local_url_input.placeholder_text = "http://localhost:1234/v1"
	_local_fields.add_child(_local_url_input)

	_local_fields.add_child(_make_label("模型:"))
	_local_model_input = LineEdit.new()
	_local_model_input.placeholder_text = "模型名称"
	_local_fields.add_child(_local_model_input)

	# Save button
	var save_btn := Button.new()
	save_btn.text = "保存 LLM 设置"
	save_btn.pressed.connect(_save_llm_settings)
	body.add_child(save_btn)


func _switch_provider(provider: String) -> void:
	_provider_claude.button_pressed = (provider == "claude")
	_provider_gemini.button_pressed = (provider == "gemini")
	_provider_local.button_pressed = (provider == "local")
	_claude_fields.visible = (provider == "claude")
	_gemini_fields.visible = (provider == "gemini")
	_local_fields.visible = (provider == "local")


func _save_llm_settings() -> void:
	var provider := "gemini"
	if _provider_claude.button_pressed:
		provider = "claude"
	elif _provider_local.button_pressed:
		provider = "local"

	if provider == "gemini":
		var key := _api_key_input.text.strip_edges()
		if not key.is_empty():
			control_requested.emit({"type": "control", "command": "set_api_key", "value": key})
	elif provider == "claude":
		var key := _claude_api_key_input.text.strip_edges()
		if not key.is_empty():
			control_requested.emit({"type": "control", "command": "set_api_key",
				"provider": "claude", "value": key})
		var model := _claude_model_input.text.strip_edges()
		if not model.is_empty():
			control_requested.emit({"type": "control", "command": "update_setting",
				"key": "claude_model", "value": model})

	# Send provider switch command
	control_requested.emit({"type": "control", "command": "update_setting",
		"key": "llm_provider", "value": provider})


# ── Game Speed ──

func _build_speed_section() -> void:
	var body := _make_collapsible_section("游戏速度")

	var tick_res := _make_slider_row(body, "世界节拍: ", 0.5, 10.0, 0.5, 3.0)
	_tick_slider = tick_res[0]
	_tick_label = tick_res[1]
	_tick_label.text = "3.0s"
	_tick_slider.value_changed.connect(func(v): _tick_label.text = "%.1fs" % v)

	var npc_min_res := _make_slider_row(body, "NPC 最短思考: ", 1, 20, 1, 5)
	_npc_min_slider = npc_min_res[0]
	_npc_min_label = npc_min_res[1]
	_npc_min_label.text = "5s"
	_npc_min_slider.value_changed.connect(func(v): _npc_min_label.text = "%.0fs" % v)

	var npc_max_res := _make_slider_row(body, "NPC 最长思考: ", 5, 60, 1, 10)
	_npc_max_slider = npc_max_res[0]
	_npc_max_label = npc_max_res[1]
	_npc_max_label.text = "10s"
	_npc_max_slider.value_changed.connect(func(v): _npc_max_label.text = "%.0fs" % v)

	var apply_btn := Button.new()
	apply_btn.text = "应用速度设置"
	apply_btn.pressed.connect(_apply_speed_settings)
	body.add_child(apply_btn)


func _apply_speed_settings() -> void:
	control_requested.emit({
		"type": "control", "command": "update_setting",
		"key": "world_tick_seconds", "value": _tick_slider.value})
	control_requested.emit({
		"type": "control", "command": "update_setting",
		"key": "npc_min_think", "value": _npc_min_slider.value})
	control_requested.emit({
		"type": "control", "command": "update_setting",
		"key": "npc_max_think", "value": _npc_max_slider.value})


# ── NPC Params ──

func _build_npc_params_section() -> void:
	var body := _make_collapsible_section("NPC 参数")

	var vis_res := _make_slider_row(body, "视野半径: ", 1, 5, 1, 2, 30)
	_vision_slider = vis_res[0]
	_vision_label = vis_res[1]
	_vision_label.text = "2"
	_vision_slider.value_changed.connect(func(v): _vision_label.text = str(int(v)))

	var hear_res := _make_slider_row(body, "听力半径: ", 3, 12, 1, 5, 30)
	_hearing_slider = hear_res[0]
	_hearing_label = hear_res[1]
	_hearing_label.text = "5"
	_hearing_slider.value_changed.connect(func(v): _hearing_label.text = str(int(v)))

	_thoughts_check = CheckButton.new()
	_thoughts_check.text = "显示 NPC 内心想法"
	_thoughts_check.button_pressed = true
	body.add_child(_thoughts_check)

	var apply_btn := Button.new()
	apply_btn.text = "应用 NPC 设置"
	apply_btn.pressed.connect(_apply_npc_params)
	body.add_child(apply_btn)


func _apply_npc_params() -> void:
	control_requested.emit({
		"type": "control", "command": "update_setting",
		"key": "npc_vision_radius", "value": int(_vision_slider.value)})
	control_requested.emit({
		"type": "control", "command": "update_setting",
		"key": "npc_hearing_radius", "value": int(_hearing_slider.value)})
	control_requested.emit({
		"type": "control", "command": "update_setting",
		"key": "show_npc_thoughts", "value": _thoughts_check.button_pressed})


# ── Display ──

func _build_display_section() -> void:
	var body := _make_collapsible_section("显示设置")

	# Window mode
	var mode_row := HBoxContainer.new()
	mode_row.add_theme_constant_override("separation", 4)
	body.add_child(mode_row)
	mode_row.add_child(_make_label("窗口模式: "))

	_window_mode_select = OptionButton.new()
	_window_mode_select.add_item("窗口化")       # 0
	_window_mode_select.add_item("全屏")         # 1
	_window_mode_select.add_item("无边框")       # 2
	_window_mode_select.custom_minimum_size.x = 100
	mode_row.add_child(_window_mode_select)

	# UI Scale
	var scale_res := _make_slider_row(body, "UI 缩放: ", 0.5, 3.0, 0.1, 1.0, 40)
	_ui_scale_slider = scale_res[0]
	_ui_scale_label = scale_res[1]
	_ui_scale_label.text = "1.0"
	_ui_scale_slider.value_changed.connect(func(v): _ui_scale_label.text = "%.1f" % v)

	# VSync
	_vsync_check = CheckButton.new()
	_vsync_check.text = "垂直同步 (VSync)"
	_vsync_check.button_pressed = true
	body.add_child(_vsync_check)

	var apply_btn := Button.new()
	apply_btn.text = "应用显示设置"
	apply_btn.pressed.connect(_apply_display_settings)
	body.add_child(apply_btn)


func _apply_display_settings() -> void:
	SettingsManager.set_setting("display", "window_mode", _window_mode_select.selected)
	SettingsManager.set_setting("display", "ui_scale", _ui_scale_slider.value)
	SettingsManager.set_setting("display", "vsync", _vsync_check.button_pressed)
	SettingsManager.apply_display_settings()


# ── Audio ──

func _build_audio_section() -> void:
	var body := _make_collapsible_section("音频设置")

	var master_res := _make_slider_row(body, "主音量: ", 0.0, 1.0, 0.05, 0.8, 40)
	_master_vol_slider = master_res[0]
	_master_vol_label = master_res[1]
	_master_vol_label.text = "80%"
	_master_vol_slider.value_changed.connect(func(v): _master_vol_label.text = "%d%%" % int(v * 100))

	var music_res := _make_slider_row(body, "音乐音量: ", 0.0, 1.0, 0.05, 0.7, 40)
	_music_vol_slider = music_res[0]
	_music_vol_label = music_res[1]
	_music_vol_label.text = "70%"
	_music_vol_slider.value_changed.connect(func(v): _music_vol_label.text = "%d%%" % int(v * 100))

	var sfx_res := _make_slider_row(body, "音效音量: ", 0.0, 1.0, 0.05, 0.8, 40)
	_sfx_vol_slider = sfx_res[0]
	_sfx_vol_label = sfx_res[1]
	_sfx_vol_label.text = "80%"
	_sfx_vol_slider.value_changed.connect(func(v): _sfx_vol_label.text = "%d%%" % int(v * 100))

	_mute_check = CheckButton.new()
	_mute_check.text = "静音"
	body.add_child(_mute_check)

	var apply_btn := Button.new()
	apply_btn.text = "应用音频设置"
	apply_btn.pressed.connect(_apply_audio_settings)
	body.add_child(apply_btn)


func _apply_audio_settings() -> void:
	SettingsManager.set_setting("audio", "master_volume", _master_vol_slider.value)
	SettingsManager.set_setting("audio", "music_volume", _music_vol_slider.value)
	SettingsManager.set_setting("audio", "sfx_volume", _sfx_vol_slider.value)
	SettingsManager.set_setting("audio", "muted", _mute_check.button_pressed)
	SettingsManager.apply_audio_settings()


# ── Network ──

func _build_network_section() -> void:
	var body := _make_collapsible_section("网络设置")

	body.add_child(_make_label("服务器地址:"))
	_server_url_input = LineEdit.new()
	_server_url_input.placeholder_text = "ws://localhost:8000/ws"
	body.add_child(_server_url_input)

	_auto_reconnect_check = CheckButton.new()
	_auto_reconnect_check.text = "自动重连"
	_auto_reconnect_check.button_pressed = true
	body.add_child(_auto_reconnect_check)

	var delay_res := _make_slider_row(body, "重连延迟: ", 1.0, 30.0, 1.0, 3.0, 40)
	_reconnect_delay_slider = delay_res[0]
	_reconnect_delay_label = delay_res[1]
	_reconnect_delay_label.text = "3s"
	_reconnect_delay_slider.value_changed.connect(func(v): _reconnect_delay_label.text = "%.0fs" % v)

	var apply_btn := Button.new()
	apply_btn.text = "应用网络设置"
	apply_btn.pressed.connect(_apply_network_settings)
	body.add_child(apply_btn)


func _apply_network_settings() -> void:
	var url := _server_url_input.text.strip_edges()
	if not url.is_empty():
		SettingsManager.set_setting("network", "server_url", url)
	SettingsManager.set_setting("network", "auto_reconnect", _auto_reconnect_check.button_pressed)
	SettingsManager.set_setting("network", "reconnect_delay_sec", _reconnect_delay_slider.value)


# ── Energy Restoration ──

func _build_energy_section() -> void:
	var body := _make_collapsible_section("体力恢复")

	var food_res := _make_slider_row(body, "食物恢复: ", 5, 100, 5, 30, 40)
	_food_energy_slider = food_res[0]
	_food_energy_label = food_res[1]
	_food_energy_label.text = "30"
	_food_energy_slider.value_changed.connect(func(v): _food_energy_label.text = "%d" % int(v))

	var sleep_res := _make_slider_row(body, "睡眠恢复: ", 10, 100, 5, 50, 40)
	_sleep_energy_slider = sleep_res[0]
	_sleep_energy_label = sleep_res[1]
	_sleep_energy_label.text = "50"
	_sleep_energy_slider.value_changed.connect(func(v): _sleep_energy_label.text = "%d" % int(v))

	var apply_btn := Button.new()
	apply_btn.text = "应用体力设置"
	apply_btn.pressed.connect(_apply_energy_settings)
	body.add_child(apply_btn)


func _apply_energy_settings() -> void:
	control_requested.emit({
		"type": "control", "command": "update_setting",
		"key": "food_energy_restore", "value": int(_food_energy_slider.value)})
	control_requested.emit({
		"type": "control", "command": "update_setting",
		"key": "sleep_energy_restore", "value": int(_sleep_energy_slider.value)})


# ── Exchange Rates ──

func _build_exchange_section() -> void:
	var body := _make_collapsible_section("交易所汇率")

	var wood_res := _make_slider_row(body, "木头价格: ", 1.0, 20.0, 0.5, 3.0, 40)
	_wood_rate_slider = wood_res[0]
	_wood_rate_label = wood_res[1]
	_wood_rate_label.text = "3.0"
	_wood_rate_slider.value_changed.connect(func(v): _wood_rate_label.text = "%.1f" % v)

	var stone_res := _make_slider_row(body, "石头价格: ", 1.0, 20.0, 0.5, 4.0, 40)
	_stone_rate_slider = stone_res[0]
	_stone_rate_label = stone_res[1]
	_stone_rate_label.text = "4.0"
	_stone_rate_slider.value_changed.connect(func(v): _stone_rate_label.text = "%.1f" % v)

	var ore_res := _make_slider_row(body, "矿石价格: ", 1.0, 30.0, 0.5, 6.0, 40)
	_ore_rate_slider = ore_res[0]
	_ore_rate_label = ore_res[1]
	_ore_rate_label.text = "6.0"
	_ore_rate_slider.value_changed.connect(func(v): _ore_rate_label.text = "%.1f" % v)

	var food_res := _make_slider_row(body, "食物成本: ", 0.5, 15.0, 0.5, 2.0, 40)
	_food_cost_slider = food_res[0]
	_food_cost_label = food_res[1]
	_food_cost_label.text = "2.0"
	_food_cost_slider.value_changed.connect(func(v): _food_cost_label.text = "%.1f" % v)

	var apply_btn := Button.new()
	apply_btn.text = "应用汇率设置"
	apply_btn.pressed.connect(_apply_exchange_settings)
	body.add_child(apply_btn)


func _apply_exchange_settings() -> void:
	control_requested.emit({
		"type": "control", "command": "update_setting",
		"key": "wood_rate", "value": _wood_rate_slider.value})
	control_requested.emit({
		"type": "control", "command": "update_setting",
		"key": "stone_rate", "value": _stone_rate_slider.value})
	control_requested.emit({
		"type": "control", "command": "update_setting",
		"key": "ore_rate", "value": _ore_rate_slider.value})
	control_requested.emit({
		"type": "control", "command": "update_setting",
		"key": "food_cost_gold", "value": _food_cost_slider.value})


# ── Controls (Weather / Resources) ──

func _build_controls_section() -> void:
	var body := _make_collapsible_section("世界控制")

	# Weather
	body.add_child(_make_label("天气:"))
	var weather_row := HBoxContainer.new()
	weather_row.add_theme_constant_override("separation", 4)
	body.add_child(weather_row)

	for w in [["晴天", "sunny"], ["雨天", "rainy"], ["暴风雨", "storm"]]:
		var btn := Button.new()
		btn.text = w[0]
		var weather_val: String = w[1]
		btn.pressed.connect(func():
			control_requested.emit({
				"type": "god_direct", "command": "set_weather", "value": weather_val}))
		weather_row.add_child(btn)
		_weather_buttons[w[1]] = btn

	# Resource spawn
	body.add_child(_make_label("生成资源:"))
	var spawn_row := HBoxContainer.new()
	spawn_row.add_theme_constant_override("separation", 4)
	body.add_child(spawn_row)

	_spawn_type = OptionButton.new()
	for item in ["wood", "stone", "ore", "food", "herb"]:
		_spawn_type.add_item(GameState.ITEM_NAMES.get(item, item))
	spawn_row.add_child(_spawn_type)

	spawn_row.add_child(_make_label("数量:"))
	_spawn_qty = SpinBox.new()
	_spawn_qty.min_value = 1
	_spawn_qty.max_value = 20
	_spawn_qty.value = 5
	spawn_row.add_child(_spawn_qty)

	var coord_row := HBoxContainer.new()
	coord_row.add_theme_constant_override("separation", 4)
	body.add_child(coord_row)

	coord_row.add_child(_make_label("X:"))
	_spawn_x = SpinBox.new()
	_spawn_x.min_value = 0
	_spawn_x.max_value = 19
	_spawn_x.value = 10
	coord_row.add_child(_spawn_x)

	coord_row.add_child(_make_label("Y:"))
	_spawn_y = SpinBox.new()
	_spawn_y.min_value = 0
	_spawn_y.max_value = 19
	_spawn_y.value = 10
	coord_row.add_child(_spawn_y)

	var spawn_btn := Button.new()
	spawn_btn.text = "生成"
	spawn_btn.pressed.connect(_on_spawn_resource)
	coord_row.add_child(spawn_btn)


func _on_spawn_resource() -> void:
	var types := ["wood", "stone", "ore", "food", "herb"]
	var idx := _spawn_type.selected
	if idx < 0 or idx >= types.size():
		return
	control_requested.emit({
		"type": "god_direct",
		"command": "spawn_resource",
		"resource_type": types[idx],
		"x": int(_spawn_x.value),
		"y": int(_spawn_y.value),
		"quantity": int(_spawn_qty.value),
	})


# ── Danger Zone ──

func _build_danger_section() -> void:
	var body := _make_collapsible_section("危险区域")
	# Collapse by default
	body.visible = false
	# Update the header text to collapsed state
	var headers := _content.get_children()
	for h in headers:
		if h is Button and h.text.find("危险区域") >= 0:
			h.text = "▶  危险区域"
			h.add_theme_color_override("font_color", Color("#e94560"))
			break

	var del_saves := Button.new()
	del_saves.text = "删除所有存档"
	del_saves.add_theme_color_override("font_color", Color("#e94560"))
	del_saves.pressed.connect(func():
		control_requested.emit({"type": "control", "command": "delete_saves"}))
	body.add_child(del_saves)

	var reset_btn := Button.new()
	reset_btn.text = "重置所有设置"
	reset_btn.add_theme_color_override("font_color", Color("#e94560"))
	reset_btn.pressed.connect(func():
		SettingsManager.reset_section("")
		_load_local_settings()
	)
	body.add_child(reset_btn)

	var home_btn := Button.new()
	home_btn.text = "返回主菜单"
	home_btn.pressed.connect(func(): go_home.emit())
	body.add_child(home_btn)


# ── Load local settings from SettingsManager ──

func _load_local_settings() -> void:
	# Display
	_window_mode_select.selected = SettingsManager.get_setting("display", "window_mode", 0)
	_ui_scale_slider.value = SettingsManager.get_setting("display", "ui_scale", 1.0)
	_ui_scale_label.text = "%.1f" % _ui_scale_slider.value
	_vsync_check.button_pressed = SettingsManager.get_setting("display", "vsync", true)

	# Audio
	_master_vol_slider.value = SettingsManager.get_setting("audio", "master_volume", 0.8)
	_master_vol_label.text = "%d%%" % int(_master_vol_slider.value * 100)
	_music_vol_slider.value = SettingsManager.get_setting("audio", "music_volume", 0.7)
	_music_vol_label.text = "%d%%" % int(_music_vol_slider.value * 100)
	_sfx_vol_slider.value = SettingsManager.get_setting("audio", "sfx_volume", 0.8)
	_sfx_vol_label.text = "%d%%" % int(_sfx_vol_slider.value * 100)
	_mute_check.button_pressed = SettingsManager.get_setting("audio", "muted", false)

	# Network
	_server_url_input.text = SettingsManager.get_setting("network", "server_url", "ws://localhost:8000/ws")
	_auto_reconnect_check.button_pressed = SettingsManager.get_setting("network", "auto_reconnect", true)
	_reconnect_delay_slider.value = SettingsManager.get_setting("network", "reconnect_delay_sec", 3.0)
	_reconnect_delay_label.text = "%.0fs" % _reconnect_delay_slider.value


# ── Helpers ──

static func _make_label(text: String) -> Label:
	var lbl := Label.new()
	lbl.text = text
	lbl.add_theme_font_size_override("font_size", 13)
	return lbl
