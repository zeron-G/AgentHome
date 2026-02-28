class_name NarrativePanel
extends PanelContainer
## Scrolling event log with BBCode color-coded entries, filter buttons, and
## collapsible toggle. Wrapped in a PanelContainer with title "事件记录".
## Max 200 lines. Inherits dark tarot theme from UIManager.

var _line_count: int = 0
const MAX_LINES := 200

# Filter categories
enum Filter { ALL, DIALOGUE, TRADE, GATHER, SYSTEM }
var _active_filter: int = Filter.ALL

# Event type → filter category mapping
const TYPE_TO_FILTER := {
	"npc_spoke": Filter.DIALOGUE,
	"player_spoke": Filter.DIALOGUE,
	"player_dialogue_replied": Filter.DIALOGUE,
	"npc_traded": Filter.TRADE,
	"trade_accepted": Filter.TRADE,
	"npc_sold": Filter.TRADE,
	"npc_bought": Filter.TRADE,
	"player_sold": Filter.TRADE,
	"player_bought": Filter.TRADE,
	"npc_gathered": Filter.GATHER,
	"player_gathered": Filter.GATHER,
	"npc_crafted": Filter.GATHER,
	"player_crafted": Filter.GATHER,
	"npc_equipped": Filter.SYSTEM,
	"player_equipped": Filter.SYSTEM,
	"furniture_built": Filter.SYSTEM,
	"weather_changed": Filter.SYSTEM,
	"market_updated": Filter.SYSTEM,
	"god_commentary": Filter.SYSTEM,
}

# Filter button labels
const FILTER_LABELS := ["全部", "对话", "交易", "采集", "系统"]

# Internal storage: each entry = {bbcode: String, filter: int}
var _entries: Array = []

# Nodes
var _title_bar: HBoxContainer
var _title_label: Label
var _toggle_button: Button
var _filter_row: HBoxContainer
var _filter_buttons: Array = []  # Array[Button]
var _log_text: RichTextLabel
var _content_box: VBoxContainer
var _collapsed: bool = false


func _ready() -> void:
	custom_minimum_size = Vector2(320, 0)
	size_flags_vertical = Control.SIZE_EXPAND_FILL

	var outer_vbox := VBoxContainer.new()
	outer_vbox.add_theme_constant_override("separation", 4)
	add_child(outer_vbox)

	# ── Title bar with collapse toggle ──
	_title_bar = HBoxContainer.new()
	_title_bar.add_theme_constant_override("separation", 6)
	outer_vbox.add_child(_title_bar)

	_title_label = Label.new()
	_title_label.text = "事件记录"
	_title_label.add_theme_font_size_override("font_size", 14)
	_title_label.add_theme_color_override("font_color", Color("#c8a832"))
	_title_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_title_bar.add_child(_title_label)

	_toggle_button = Button.new()
	_toggle_button.text = "▲收起"
	_toggle_button.custom_minimum_size.x = 64
	_toggle_button.pressed.connect(_on_toggle_pressed)
	_title_bar.add_child(_toggle_button)

	# ── Collapsible content ──
	_content_box = VBoxContainer.new()
	_content_box.add_theme_constant_override("separation", 4)
	outer_vbox.add_child(_content_box)

	# ── Filter buttons row ──
	_filter_row = HBoxContainer.new()
	_filter_row.add_theme_constant_override("separation", 2)
	_content_box.add_child(_filter_row)

	for i in FILTER_LABELS.size():
		var btn := Button.new()
		btn.text = FILTER_LABELS[i]
		btn.custom_minimum_size.x = 44
		btn.toggle_mode = true
		btn.button_pressed = (i == 0)
		var filter_id := i
		btn.pressed.connect(func(): _set_filter(filter_id))
		_filter_row.add_child(btn)
		_filter_buttons.append(btn)

	# Highlight active filter button
	_style_active_filter()

	# ── Separator ──
	_content_box.add_child(HSeparator.new())

	# ── Log text ──
	_log_text = RichTextLabel.new()
	_log_text.bbcode_enabled = true
	_log_text.scroll_following = true
	_log_text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_log_text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_log_text.selection_enabled = true
	_content_box.add_child(_log_text)


# ── Public API (kept compatible) ──

func append_event(evt: Dictionary) -> void:
	var summary: String = evt.get("summary", "")
	if summary.is_empty():
		return
	var evt_type: String = evt.get("type", "")
	if evt_type == "npc_moved":
		return

	var color: String = GameState.EVENT_COLORS.get(evt_type, "#888899")
	var filter_cat: int = TYPE_TO_FILTER.get(evt_type, Filter.SYSTEM)
	var time_prefix: String = _build_time_prefix()
	var bbcode: String = "[color=#8888a0]%s[/color] [color=%s]%s[/color]" % [time_prefix, color, summary]

	_entries.append({"bbcode": bbcode, "filter": filter_cat})
	if _entries.size() > MAX_LINES:
		_entries = _entries.slice(_entries.size() - MAX_LINES)

	# If this entry passes current filter, append to display
	if _active_filter == Filter.ALL or filter_cat == _active_filter:
		_append_to_display(bbcode)


func append_system(bbcode: String) -> void:
	var time_prefix: String = _build_time_prefix()
	var full_bbcode: String = "[color=#8888a0]%s[/color] %s" % [time_prefix, bbcode]
	_entries.append({"bbcode": full_bbcode, "filter": Filter.SYSTEM})
	if _entries.size() > MAX_LINES:
		_entries = _entries.slice(_entries.size() - MAX_LINES)
	if _active_filter == Filter.ALL or _active_filter == Filter.SYSTEM:
		_append_to_display(full_bbcode)


func append_line(bbcode: String) -> void:
	# Generic line — categorize as SYSTEM
	_entries.append({"bbcode": bbcode, "filter": Filter.SYSTEM})
	if _entries.size() > MAX_LINES:
		_entries = _entries.slice(_entries.size() - MAX_LINES)
	if _active_filter == Filter.ALL or _active_filter == Filter.SYSTEM:
		_append_to_display(bbcode)


# ── Internals ──

func _append_to_display(bbcode: String) -> void:
	if _line_count > 0:
		_log_text.append_text("\n")
	_log_text.append_text(bbcode)
	_line_count += 1
	# Trim display if too many lines shown
	if _line_count > MAX_LINES:
		_rebuild_display()


func _build_time_prefix() -> String:
	var td: Dictionary = GameState.time_data
	if td.is_empty():
		return ""
	var day: int = td.get("day", 1)
	var time_str: String = td.get("time_str", "")
	# time_str is like "Day 1 06:00", extract just the HH:MM part
	var hm: String = ""
	if time_str.contains(" "):
		var parts := time_str.split(" ")
		if parts.size() >= 3:
			hm = parts[2]
		else:
			hm = time_str
	else:
		hm = time_str
	return "[Day %d %s]" % [day, hm]


func _set_filter(filter_id: int) -> void:
	_active_filter = filter_id
	# Update button toggle states
	for i in _filter_buttons.size():
		_filter_buttons[i].button_pressed = (i == filter_id)
	_style_active_filter()
	_rebuild_display()


func _style_active_filter() -> void:
	for i in _filter_buttons.size():
		if i == _active_filter:
			_filter_buttons[i].add_theme_color_override("font_color", Color("#c8a832"))
		else:
			_filter_buttons[i].remove_theme_color_override("font_color")


func _rebuild_display() -> void:
	_log_text.clear()
	_log_text.text = ""
	_line_count = 0
	for entry in _entries:
		if _active_filter == Filter.ALL or entry["filter"] == _active_filter:
			_append_to_display(entry["bbcode"])


func _on_toggle_pressed() -> void:
	_collapsed = not _collapsed
	_content_box.visible = not _collapsed
	_toggle_button.text = "▼展开" if _collapsed else "▲收起"
