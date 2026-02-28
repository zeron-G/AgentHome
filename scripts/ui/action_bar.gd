class_name ActionBar
extends VBoxContainer
## Bottom action bar: 3x3 movement grid + quick actions + context-sensitive buttons.

signal action_requested(action: Dictionary)

var _move_grid: GridContainer
var _action_row: HBoxContainer
var _context_row: HBoxContainer
var _god_indicator: Label

# Context state
var _at_exchange: bool = false
var _is_god_mode: bool = false


func _ready() -> void:
	add_theme_constant_override("separation", 4)

	var main_row := HBoxContainer.new()
	main_row.add_theme_constant_override("separation", 8)
	add_child(main_row)

	# ── Movement: 3x3 grid (NW,N,NE / W,·,E / SW,S,SE) ──
	var move_frame := PanelContainer.new()
	var frame_style := StyleBoxFlat.new()
	frame_style.bg_color = Color("#14141eea")
	frame_style.border_color = Color("#2a2a3e")
	frame_style.set_border_width_all(1)
	frame_style.set_corner_radius_all(4)
	frame_style.content_margin_left = 2
	frame_style.content_margin_right = 2
	frame_style.content_margin_top = 2
	frame_style.content_margin_bottom = 2
	move_frame.add_theme_stylebox_override("panel", frame_style)
	main_row.add_child(move_frame)

	_move_grid = GridContainer.new()
	_move_grid.columns = 3
	_move_grid.add_theme_constant_override("h_separation", 1)
	_move_grid.add_theme_constant_override("v_separation", 1)
	move_frame.add_child(_move_grid)

	# Grid layout:  NW  N  NE
	#                W  ·   E
	#               SW  S  SE
	var grid_data := [
		{"label": "NW", "dx": -1, "dy": -1, "hint": "Q"},
		{"label": "N",  "dx": 0,  "dy": -1, "hint": "W"},
		{"label": "NE", "dx": 1,  "dy": -1, "hint": "E"},
		{"label": "W",  "dx": -1, "dy": 0,  "hint": "A"},
		{"label": "·",  "dx": 0,  "dy": 0,  "hint": ""},   # center: no-op / wait
		{"label": "E",  "dx": 1,  "dy": 0,  "hint": "D"},
		{"label": "SW", "dx": -1, "dy": 1,  "hint": "Z"},
		{"label": "S",  "dx": 0,  "dy": 1,  "hint": "S"},
		{"label": "SE", "dx": 1,  "dy": 1,  "hint": "C"},
	]
	for gd in grid_data:
		var btn := Button.new()
		btn.custom_minimum_size = Vector2(36, 28)
		btn.add_theme_font_size_override("font_size", 11)
		if gd["hint"] != "":
			btn.text = "%s" % gd["label"]
			btn.tooltip_text = "[%s] 移动%s" % [gd["hint"], gd["label"]]
		else:
			btn.text = "·"
			btn.tooltip_text = "等待"
		var dx: int = gd["dx"]
		var dy: int = gd["dy"]
		if dx == 0 and dy == 0:
			# Center: wait/rest action
			btn.pressed.connect(func(): action_requested.emit({"action": "rest"}))
		else:
			btn.pressed.connect(func(): action_requested.emit({"action": "move", "dx": dx, "dy": dy}))
		_move_grid.add_child(btn)

	# ── Separator ──
	var vsep := VSeparator.new()
	vsep.add_theme_color_override("separator", Color("#2a2a3e"))
	main_row.add_child(vsep)

	# ── Quick actions ──
	var actions_vbox := VBoxContainer.new()
	actions_vbox.add_theme_constant_override("separation", 2)
	main_row.add_child(actions_vbox)

	_action_row = HBoxContainer.new()
	_action_row.add_theme_constant_override("separation", 4)
	actions_vbox.add_child(_action_row)

	var quick_actions := [
		["采集", "gather", "G"],
		["吃", "eat", "E"],
		["休息", "rest", "R"],
		["睡觉", "sleep", "Z"],
	]
	for act in quick_actions:
		var btn := Button.new()
		btn.text = "%s" % act[0]
		btn.tooltip_text = "[%s] %s" % [act[2], act[0]]
		btn.add_theme_font_size_override("font_size", 12)
		var action_name: String = act[1]
		btn.pressed.connect(func(): action_requested.emit({"action": action_name}))
		_action_row.add_child(btn)

	# ── Context-sensitive row (exchange buttons, etc.) ──
	_context_row = HBoxContainer.new()
	_context_row.add_theme_constant_override("separation", 4)
	_context_row.visible = false
	actions_vbox.add_child(_context_row)

	# ── God mode indicator ──
	_god_indicator = Label.new()
	_god_indicator.text = "GOD MODE"
	_god_indicator.add_theme_font_size_override("font_size", 11)
	_god_indicator.add_theme_color_override("font_color", Color("#9c27b0"))
	_god_indicator.visible = false
	main_row.add_child(_god_indicator)


func update_context(at_exchange: bool, is_god_mode: bool) -> void:
	_at_exchange = at_exchange
	_is_god_mode = is_god_mode

	# Rebuild context row
	for child in _context_row.get_children():
		child.queue_free()

	if at_exchange:
		_context_row.visible = true

		var buy_btn := Button.new()
		buy_btn.text = "买入"
		buy_btn.tooltip_text = "在交易所买入物品"
		buy_btn.add_theme_font_size_override("font_size", 12)
		buy_btn.pressed.connect(func(): action_requested.emit({"action": "buy_menu"}))
		_context_row.add_child(buy_btn)

		var sell_btn := Button.new()
		sell_btn.text = "卖出"
		sell_btn.tooltip_text = "在交易所卖出物品"
		sell_btn.add_theme_font_size_override("font_size", 12)
		sell_btn.pressed.connect(func(): action_requested.emit({"action": "sell_menu"}))
		_context_row.add_child(sell_btn)

		var exchange_lbl := Label.new()
		exchange_lbl.text = "交易所"
		exchange_lbl.add_theme_font_size_override("font_size", 11)
		exchange_lbl.add_theme_color_override("font_color", Color("#c8a832"))
		_context_row.add_child(exchange_lbl)
	else:
		_context_row.visible = false

	# God mode indicator
	_god_indicator.visible = is_god_mode
