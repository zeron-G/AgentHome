class_name SidePanel
extends PanelContainer
## Right-side 300px tabbed panel container with 4 tabs:
##   状态 (Status)   - player info, inventory, crafting
##   角色 (Characters) - NPC list sorted by distance
##   经济 (Economy)  - market prices, buy/sell
##   设置 (Settings) - game configuration

const PANEL_WIDTH := 300

var tab_container: TabContainer

## Cached tab content nodes for external access
var status_tab: Control
var characters_tab: Control
var economy_tab: Control
var settings_tab: Control

## Animation
var _is_open: bool = true
var _toggle_button: Button

signal tab_changed(index: int)
signal toggle_requested(is_open: bool)


func _ready() -> void:
	# Panel sizing and anchoring: right edge, full height minus header/action bars
	custom_minimum_size = Vector2(PANEL_WIDTH, 0)
	anchor_left = 1.0
	anchor_right = 1.0
	anchor_top = 0.0
	anchor_bottom = 1.0
	offset_left = -PANEL_WIDTH
	offset_right = 0
	offset_top = 44    # below header bar
	offset_bottom = -44  # above action bar
	size_flags_vertical = Control.SIZE_EXPAND_FILL

	_build_ui()


func _build_ui() -> void:
	var main_vbox := VBoxContainer.new()
	main_vbox.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	main_vbox.add_theme_constant_override("separation", 0)
	add_child(main_vbox)

	# Toggle collapse button row
	var toggle_row := HBoxContainer.new()
	toggle_row.alignment = BoxContainer.ALIGNMENT_END
	main_vbox.add_child(toggle_row)

	_toggle_button = Button.new()
	_toggle_button.text = "▶ 收起"
	_toggle_button.add_theme_font_size_override("font_size", 11)
	_toggle_button.pressed.connect(_on_toggle_pressed)
	toggle_row.add_child(_toggle_button)

	# Tab container
	tab_container = TabContainer.new()
	tab_container.size_flags_vertical = Control.SIZE_EXPAND_FILL
	tab_container.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	tab_container.tab_alignment = TabBar.ALIGNMENT_CENTER
	tab_container.tab_changed.connect(_on_tab_changed)
	main_vbox.add_child(tab_container)


## Add a tab with a title and content node. Returns the content node for chaining.
func add_tab(title: String, content: Control) -> Control:
	content.name = title
	content.size_flags_vertical = Control.SIZE_EXPAND_FILL
	content.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	tab_container.add_child(content)
	return content


## Convenience: populate all 4 tabs with pre-built content nodes.
func setup_tabs(p_status: Control, p_characters: Control, p_economy: Control, p_settings: Control) -> void:
	status_tab = add_tab("状态", p_status)
	characters_tab = add_tab("角色", p_characters)
	economy_tab = add_tab("经济", p_economy)
	settings_tab = add_tab("设置", p_settings)


func switch_to_tab(index: int) -> void:
	if index >= 0 and index < tab_container.get_tab_count():
		tab_container.current_tab = index


func switch_to_tab_by_name(tab_name: String) -> void:
	for i in range(tab_container.get_tab_count()):
		if tab_container.get_tab_title(i) == tab_name:
			tab_container.current_tab = i
			return


func get_current_tab_index() -> int:
	return tab_container.current_tab


func get_current_tab_name() -> String:
	var idx := tab_container.current_tab
	if idx >= 0 and idx < tab_container.get_tab_count():
		return tab_container.get_tab_title(idx)
	return ""


## Slide the panel open with animation.
func open_panel() -> void:
	if _is_open:
		return
	_is_open = true
	_toggle_button.text = "▶ 收起"
	var tween := create_tween().set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_CUBIC)
	tween.tween_property(self, "offset_left", -PANEL_WIDTH, 0.25)
	toggle_requested.emit(true)


## Slide the panel closed with animation.
func close_panel() -> void:
	if not _is_open:
		return
	_is_open = false
	_toggle_button.text = "◀ 展开"
	var tween := create_tween().set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_CUBIC)
	tween.tween_property(self, "offset_left", 0, 0.25)
	toggle_requested.emit(false)


func is_open() -> bool:
	return _is_open


func _on_toggle_pressed() -> void:
	if _is_open:
		close_panel()
	else:
		open_panel()


func _on_tab_changed(index: int) -> void:
	tab_changed.emit(index)


## Handle keyboard shortcuts for tab switching
func _unhandled_input(event: InputEvent) -> void:
	if not visible:
		return
	if event is InputEventKey and event.pressed and not event.echo:
		# Tab key to toggle panel visibility
		if event.keycode == KEY_TAB and event.shift_pressed:
			_on_toggle_pressed()
			get_viewport().set_input_as_handled()
			return
		# Number keys 1-4 to switch tabs (with Alt held)
		if event.alt_pressed:
			var tab_idx := -1
			match event.keycode:
				KEY_1: tab_idx = 0
				KEY_2: tab_idx = 1
				KEY_3: tab_idx = 2
				KEY_4: tab_idx = 3
			if tab_idx >= 0 and tab_idx < tab_container.get_tab_count():
				switch_to_tab(tab_idx)
				get_viewport().set_input_as_handled()
