class_name MarketPanel
extends VBoxContainer
## Economy panel: price table with icons & sparklines, buy/sell controls, trade log.

signal action_requested(action: Dictionary)

var _price_container: VBoxContainer
var _trade_section: VBoxContainer
var _trade_item_select: OptionButton
var _trade_qty_input: SpinBox
var _buy_btn: Button
var _sell_btn: Button
var _trade_log: VBoxContainer
var _trade_log_entries: Array = []
const MAX_TRADE_LOG := 15

const TRADEABLE_ITEMS := ["wood", "stone", "ore", "food", "herb", "rope", "potion", "tool", "bread"]

# Caches
var _icon_cache: Dictionary = {}
# Price history for sparklines: item_key -> Array[float] (last 10 prices)
var _price_history: Dictionary = {}


func _ready() -> void:
	add_theme_constant_override("separation", 6)
	_preload_icons()

	# Title
	var title := Label.new()
	title.text = "市场价格"
	title.add_theme_font_size_override("font_size", 16)
	title.add_theme_color_override("font_color", Color("#c8a832"))
	add_child(title)

	# Price table header
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 0)
	add_child(header)
	var col_headers := [
		{"text": "", "width": 20},      # icon
		{"text": "物品", "width": 46},
		{"text": "当前", "width": 44},
		{"text": "基准", "width": 44},
		{"text": "趋势", "width": 36},
		{"text": "涨跌%", "width": 52},
		{"text": "走势", "width": 60},   # sparkline
	]
	for col in col_headers:
		var lbl := Label.new()
		lbl.text = col["text"]
		lbl.add_theme_font_size_override("font_size", 11)
		lbl.add_theme_color_override("font_color", Color("#8888a0"))
		lbl.custom_minimum_size.x = col["width"]
		header.add_child(lbl)

	# Price rows
	var price_scroll := ScrollContainer.new()
	price_scroll.custom_minimum_size.y = 180
	add_child(price_scroll)

	_price_container = VBoxContainer.new()
	_price_container.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_price_container.add_theme_constant_override("separation", 1)
	price_scroll.add_child(_price_container)

	add_child(_make_separator())

	# Trade section (only visible at exchange)
	_trade_section = VBoxContainer.new()
	_trade_section.visible = false
	_trade_section.add_theme_constant_override("separation", 4)
	add_child(_trade_section)

	# Trade section border style
	var trade_panel := PanelContainer.new()
	var trade_style := StyleBoxFlat.new()
	trade_style.bg_color = Color("#0a0a14")
	trade_style.border_color = Color("#c8a832")
	trade_style.set_border_width_all(1)
	trade_style.set_corner_radius_all(4)
	trade_style.content_margin_left = 8
	trade_style.content_margin_right = 8
	trade_style.content_margin_top = 6
	trade_style.content_margin_bottom = 6
	trade_panel.add_theme_stylebox_override("panel", trade_style)

	var trade_inner := VBoxContainer.new()
	trade_inner.add_theme_constant_override("separation", 4)
	trade_panel.add_child(trade_inner)
	_trade_section.add_child(trade_panel)

	var trade_title := Label.new()
	trade_title.text = "交易所操作"
	trade_title.add_theme_font_size_override("font_size", 14)
	trade_title.add_theme_color_override("font_color", Color("#c8a832"))
	trade_inner.add_child(trade_title)

	var trade_row := HBoxContainer.new()
	trade_row.add_theme_constant_override("separation", 4)
	trade_inner.add_child(trade_row)

	_trade_item_select = OptionButton.new()
	for item in TRADEABLE_ITEMS:
		_trade_item_select.add_item(GameState.ITEM_NAMES.get(item, item))
	_trade_item_select.custom_minimum_size.x = 80
	trade_row.add_child(_trade_item_select)

	_trade_qty_input = SpinBox.new()
	_trade_qty_input.min_value = 1
	_trade_qty_input.max_value = 99
	_trade_qty_input.value = 1
	_trade_qty_input.custom_minimum_size.x = 70
	trade_row.add_child(_trade_qty_input)

	_buy_btn = Button.new()
	_buy_btn.text = "买入"
	_buy_btn.pressed.connect(_on_buy)
	trade_row.add_child(_buy_btn)

	_sell_btn = Button.new()
	_sell_btn.text = "卖出"
	_sell_btn.pressed.connect(_on_sell)
	trade_row.add_child(_sell_btn)

	add_child(_make_separator())

	# Trade log
	var log_title := Label.new()
	log_title.text = "交易记录"
	log_title.add_theme_font_size_override("font_size", 14)
	log_title.add_theme_color_override("font_color", Color("#e0e0e8"))
	add_child(log_title)

	var log_scroll := ScrollContainer.new()
	log_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	log_scroll.custom_minimum_size.y = 80
	add_child(log_scroll)

	_trade_log = VBoxContainer.new()
	_trade_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	log_scroll.add_child(_trade_log)


func update_market(market: Dictionary, at_exchange: bool) -> void:
	# Update price table
	for child in _price_container.get_children():
		child.queue_free()

	var prices: Dictionary = market.get("prices", {})
	for item in TRADEABLE_ITEMS:
		if not prices.has(item):
			continue
		var p: Dictionary = prices[item]
		var current_price: float = p.get("current", 0)

		# Track price history for sparkline
		if not _price_history.has(item):
			_price_history[item] = []
		_price_history[item].append(current_price)
		if _price_history[item].size() > 10:
			_price_history[item] = _price_history[item].slice(_price_history[item].size() - 10)

		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 0)

		# Item icon
		var icon := _make_item_icon(item)
		if icon:
			icon.custom_minimum_size.x = 20
			row.add_child(icon)
		else:
			var spacer := Control.new()
			spacer.custom_minimum_size.x = 20
			row.add_child(spacer)

		# Item name
		var name_lbl := Label.new()
		name_lbl.text = GameState.ITEM_NAMES.get(item, item)
		name_lbl.custom_minimum_size.x = 46
		name_lbl.add_theme_font_size_override("font_size", 12)
		row.add_child(name_lbl)

		# Current price
		var cur_lbl := Label.new()
		cur_lbl.text = "%.1f" % current_price
		cur_lbl.custom_minimum_size.x = 44
		cur_lbl.add_theme_font_size_override("font_size", 12)
		cur_lbl.add_theme_color_override("font_color", Color("#e0e0e8"))
		row.add_child(cur_lbl)

		# Base price
		var base_lbl := Label.new()
		base_lbl.text = "%.1f" % p.get("base", 0)
		base_lbl.custom_minimum_size.x = 44
		base_lbl.add_theme_font_size_override("font_size", 12)
		base_lbl.add_theme_color_override("font_color", Color("#8888a0"))
		row.add_child(base_lbl)

		# Trend arrow
		var trend: String = p.get("trend", "-")
		var trend_lbl := Label.new()
		trend_lbl.text = trend
		trend_lbl.custom_minimum_size.x = 36
		trend_lbl.add_theme_font_size_override("font_size", 12)
		if trend == "↑":
			trend_lbl.add_theme_color_override("font_color", Color("#4ecca3"))
		elif trend == "↓":
			trend_lbl.add_theme_color_override("font_color", Color("#e94560"))
		else:
			trend_lbl.add_theme_color_override("font_color", Color("#8888a0"))
		row.add_child(trend_lbl)

		# Change percentage — vivid colors
		var change: float = p.get("change_pct", 0)
		var change_lbl := Label.new()
		change_lbl.text = "%+.1f%%" % change
		change_lbl.custom_minimum_size.x = 52
		change_lbl.add_theme_font_size_override("font_size", 12)
		if change > 5.0:
			change_lbl.add_theme_color_override("font_color", Color("#00ff88"))
		elif change > 0:
			change_lbl.add_theme_color_override("font_color", Color("#4ecca3"))
		elif change < -5.0:
			change_lbl.add_theme_color_override("font_color", Color("#ff2244"))
		elif change < 0:
			change_lbl.add_theme_color_override("font_color", Color("#e94560"))
		else:
			change_lbl.add_theme_color_override("font_color", Color("#8888a0"))
		row.add_child(change_lbl)

		# Mini sparkline
		var sparkline := SparklineControl.new()
		sparkline.custom_minimum_size = Vector2(60, 16)
		sparkline.data_points = _price_history.get(item, [])
		row.add_child(sparkline)

		_price_container.add_child(row)

	# Trade section visibility
	_trade_section.visible = at_exchange


func add_trade_event(evt: Dictionary) -> void:
	var summary: String = evt.get("summary", "")
	if summary.is_empty():
		return
	var evt_type: String = evt.get("type", "")
	var trade_types := ["npc_traded", "trade_accepted", "npc_sold", "npc_bought",
		"player_sold", "player_bought"]
	if evt_type not in trade_types:
		return

	_trade_log_entries.append(evt)
	if _trade_log_entries.size() > MAX_TRADE_LOG:
		_trade_log_entries = _trade_log_entries.slice(_trade_log_entries.size() - MAX_TRADE_LOG)

	# Rebuild log display
	for child in _trade_log.get_children():
		child.queue_free()
	for entry in _trade_log_entries:
		var lbl := Label.new()
		lbl.text = entry.get("summary", "")
		lbl.add_theme_font_size_override("font_size", 11)
		var entry_type: String = entry.get("type", "")
		if entry_type.find("bought") >= 0:
			lbl.add_theme_color_override("font_color", Color("#e94560"))
		elif entry_type.find("sold") >= 0:
			lbl.add_theme_color_override("font_color", Color("#4ecca3"))
		else:
			lbl.add_theme_color_override("font_color", Color("#f5a623"))
		lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		_trade_log.add_child(lbl)


func _on_buy() -> void:
	var idx := _trade_item_select.selected
	if idx < 0 or idx >= TRADEABLE_ITEMS.size():
		return
	var item: String = TRADEABLE_ITEMS[idx]
	var qty: int = int(_trade_qty_input.value)
	action_requested.emit({"action": "buy", "buy_item": item, "buy_qty": qty})


func _on_sell() -> void:
	var idx := _trade_item_select.selected
	if idx < 0 or idx >= TRADEABLE_ITEMS.size():
		return
	var item: String = TRADEABLE_ITEMS[idx]
	var qty: int = int(_trade_qty_input.value)
	action_requested.emit({"action": "sell", "sell_item": item, "sell_qty": qty})


# ── Helpers ──

func _preload_icons() -> void:
	var items := ["wood", "stone", "ore", "food", "herb", "rope",
		"potion", "tool", "bread", "gold"]
	for item in items:
		var path := "res://resources/art/icons/%s.png" % item
		if ResourceLoader.exists(path):
			_icon_cache[item] = load(path)


func _make_item_icon(item_key: String) -> TextureRect:
	if not _icon_cache.has(item_key):
		return null
	var tex_rect := TextureRect.new()
	tex_rect.texture = _icon_cache[item_key]
	tex_rect.custom_minimum_size = Vector2(16, 16)
	tex_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	tex_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	return tex_rect


func _make_separator() -> HSeparator:
	var sep := HSeparator.new()
	sep.add_theme_color_override("separator", Color("#2a2a3e"))
	return sep


# ── Inner class: sparkline custom draw control ──

class SparklineControl extends Control:
	var data_points: Array = []

	func _draw() -> void:
		if data_points.size() < 2:
			return

		var w := size.x
		var h := size.y
		var margin := 2.0

		# Find min/max for normalization
		var min_val: float = data_points[0]
		var max_val: float = data_points[0]
		for v in data_points:
			if v < min_val:
				min_val = v
			if v > max_val:
				max_val = v

		var val_range := max_val - min_val
		if val_range < 0.01:
			val_range = 1.0

		# Determine color based on trend (last vs first)
		var first_val: float = data_points[0]
		var last_val: float = data_points[data_points.size() - 1]
		var line_color: Color
		if last_val > first_val:
			line_color = Color("#4ecca3")
		elif last_val < first_val:
			line_color = Color("#e94560")
		else:
			line_color = Color("#8888a0")

		# Draw line segments
		var points: PackedVector2Array = []
		var step_x := (w - margin * 2) / float(data_points.size() - 1)
		for i in data_points.size():
			var normalized := (float(data_points[i]) - min_val) / val_range
			var x := margin + i * step_x
			var y := h - margin - normalized * (h - margin * 2)
			points.append(Vector2(x, y))

		if points.size() >= 2:
			draw_polyline(points, line_color, 1.5, true)

			# Draw dot at last point
			var last_point := points[points.size() - 1]
			draw_circle(last_point, 2.0, line_color)
