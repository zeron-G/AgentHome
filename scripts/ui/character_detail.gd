class_name CharacterDetail
extends PanelContainer
## Full character detail modal popup.
## Shows when player double-clicks an NPC or clicks "详情" in NPC list.
##
## Layout:
## ┌──────────────────────────────────────┐
## │ [塔罗牌面]  禾 - III 皇后       [✕] │
## │ 母亲 | 情绪: 开心                    │
## ├──────────────────────────────────────┤
## │ [立绘区]  | 性格: 温暖包容...         │
## │           | 目标: 采集食物...          │
## │           | 计划: ✓去森林 →采集...     │
## ├──────────────────────────────────────┤
## │ 关系网:                              │
## │ 穗 ← 母女·过度保护                   │
## │ 山 ← 尊敬  |  棠 ← 关心             │
## ├──────────────────────────────────────┤
## │ 世界观: 这片土地养育了我...            │
## ├──────────────────────────────────────┤
## │ 库存: 木×3  食×2  金×10              │
## ├──────────────────────────────────────┤
## │        [说话]    [交易]               │
## └──────────────────────────────────────┘

signal talk_requested(npc_id: String)
signal trade_requested(npc_id: String)
signal close_requested

var current_npc_id: String = ""

# ── UI element references ──
var _title_label: Label
var _subtitle_label: Label
var _close_button: Button
var _portrait_rect: TextureRect
var _personality_label: RichTextLabel
var _goal_label: Label
var _plan_list: VBoxContainer
var _mood_label: Label
var _energy_bar: ProgressBar
var _relationships_container: VBoxContainer
var _worldview_label: RichTextLabel
var _inventory_container: HFlowContainer
var _talk_button: Button
var _trade_button: Button
var _speech_style_label: Label

# Dimmed background overlay
var _dim_overlay: ColorRect


func _ready() -> void:
	# Center on screen, 520x620
	custom_minimum_size = Vector2(520, 620)
	anchor_left = 0.5
	anchor_right = 0.5
	anchor_top = 0.5
	anchor_bottom = 0.5
	offset_left = -260
	offset_right = 260
	offset_top = -310
	offset_bottom = 310
	mouse_filter = Control.MOUSE_FILTER_STOP

	visible = false
	_build_ui()


func _build_ui() -> void:
	var scroll := ScrollContainer.new()
	scroll.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	add_child(scroll)

	var main_vbox := VBoxContainer.new()
	main_vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	main_vbox.add_theme_constant_override("separation", 8)
	scroll.add_child(main_vbox)

	# ══════ Header ══════
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 8)
	main_vbox.add_child(header)

	_title_label = Label.new()
	_title_label.add_theme_font_size_override("font_size", 20)
	_title_label.add_theme_color_override("font_color", Color("#c8a832"))
	_title_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(_title_label)

	_close_button = Button.new()
	_close_button.text = "✕"
	_close_button.custom_minimum_size = Vector2(32, 32)
	_close_button.pressed.connect(_on_close)
	header.add_child(_close_button)

	# Subtitle: role + mood
	_subtitle_label = Label.new()
	_subtitle_label.add_theme_font_size_override("font_size", 13)
	_subtitle_label.add_theme_color_override("font_color", Color("#8888a0"))
	main_vbox.add_child(_subtitle_label)

	main_vbox.add_child(HSeparator.new())

	# ══════ Content: portrait + info columns ══════
	var content_hbox := HBoxContainer.new()
	content_hbox.add_theme_constant_override("separation", 12)
	main_vbox.add_child(content_hbox)

	# Portrait column
	var portrait_vbox := VBoxContainer.new()
	portrait_vbox.add_theme_constant_override("separation", 4)
	content_hbox.add_child(portrait_vbox)

	_portrait_rect = TextureRect.new()
	_portrait_rect.custom_minimum_size = Vector2(128, 192)
	_portrait_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_portrait_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	portrait_vbox.add_child(_portrait_rect)

	# Energy bar under portrait
	_energy_bar = ProgressBar.new()
	_energy_bar.max_value = 100
	_energy_bar.value = 100
	_energy_bar.show_percentage = false
	_energy_bar.custom_minimum_size = Vector2(128, 12)
	portrait_vbox.add_child(_energy_bar)

	_mood_label = Label.new()
	_mood_label.add_theme_font_size_override("font_size", 12)
	_mood_label.add_theme_color_override("font_color", Color("#8888a0"))
	_mood_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	portrait_vbox.add_child(_mood_label)

	# Info column
	var info_vbox := VBoxContainer.new()
	info_vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	info_vbox.add_theme_constant_override("separation", 6)
	content_hbox.add_child(info_vbox)

	# Personality
	var pers_header := Label.new()
	pers_header.text = "性格"
	pers_header.add_theme_font_size_override("font_size", 13)
	pers_header.add_theme_color_override("font_color", Color("#c8a832"))
	info_vbox.add_child(pers_header)

	_personality_label = RichTextLabel.new()
	_personality_label.bbcode_enabled = true
	_personality_label.fit_content = true
	_personality_label.custom_minimum_size.y = 40
	_personality_label.scroll_active = false
	info_vbox.add_child(_personality_label)

	# Speech style
	_speech_style_label = Label.new()
	_speech_style_label.add_theme_font_size_override("font_size", 12)
	_speech_style_label.add_theme_color_override("font_color", Color("#8888a0"))
	_speech_style_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	info_vbox.add_child(_speech_style_label)

	# Goal
	_goal_label = Label.new()
	_goal_label.add_theme_font_size_override("font_size", 13)
	_goal_label.add_theme_color_override("font_color", Color("#4ecca3"))
	_goal_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	info_vbox.add_child(_goal_label)

	# Plan steps
	var plan_header := Label.new()
	plan_header.text = "计划"
	plan_header.add_theme_font_size_override("font_size", 13)
	plan_header.add_theme_color_override("font_color", Color("#c8a832"))
	info_vbox.add_child(plan_header)

	_plan_list = VBoxContainer.new()
	_plan_list.add_theme_constant_override("separation", 2)
	info_vbox.add_child(_plan_list)

	main_vbox.add_child(HSeparator.new())

	# ══════ Relationships ══════
	var rel_header := Label.new()
	rel_header.text = "关系网"
	rel_header.add_theme_font_size_override("font_size", 14)
	rel_header.add_theme_color_override("font_color", Color("#c8a832"))
	main_vbox.add_child(rel_header)

	_relationships_container = VBoxContainer.new()
	_relationships_container.add_theme_constant_override("separation", 2)
	main_vbox.add_child(_relationships_container)

	main_vbox.add_child(HSeparator.new())

	# ══════ Worldview ══════
	var wv_header := Label.new()
	wv_header.text = "世界观"
	wv_header.add_theme_font_size_override("font_size", 14)
	wv_header.add_theme_color_override("font_color", Color("#c8a832"))
	main_vbox.add_child(wv_header)

	_worldview_label = RichTextLabel.new()
	_worldview_label.bbcode_enabled = true
	_worldview_label.fit_content = true
	_worldview_label.custom_minimum_size.y = 40
	_worldview_label.scroll_active = false
	main_vbox.add_child(_worldview_label)

	main_vbox.add_child(HSeparator.new())

	# ══════ Inventory ══════
	var inv_header := Label.new()
	inv_header.text = "库存"
	inv_header.add_theme_font_size_override("font_size", 14)
	inv_header.add_theme_color_override("font_color", Color("#c8a832"))
	main_vbox.add_child(inv_header)

	_inventory_container = HFlowContainer.new()
	_inventory_container.add_theme_constant_override("h_separation", 10)
	_inventory_container.add_theme_constant_override("v_separation", 4)
	main_vbox.add_child(_inventory_container)

	main_vbox.add_child(HSeparator.new())

	# ══════ Action Buttons ══════
	var btn_bar := HBoxContainer.new()
	btn_bar.alignment = BoxContainer.ALIGNMENT_CENTER
	btn_bar.add_theme_constant_override("separation", 16)
	main_vbox.add_child(btn_bar)

	_talk_button = Button.new()
	_talk_button.text = "说话"
	_talk_button.custom_minimum_size = Vector2(80, 32)
	_talk_button.pressed.connect(func(): talk_requested.emit(current_npc_id))
	btn_bar.add_child(_talk_button)

	_trade_button = Button.new()
	_trade_button.text = "交易"
	_trade_button.custom_minimum_size = Vector2(80, 32)
	_trade_button.pressed.connect(func(): trade_requested.emit(current_npc_id))
	btn_bar.add_child(_trade_button)


# ── Public API ──

func show_character(npc_data: Dictionary) -> void:
	if not npc_data is Dictionary or npc_data.is_empty():
		return
	current_npc_id = npc_data.get("id", "")
	var profile: Dictionary = _safe_dict(npc_data, "profile")

	# Title: "禾 - III 皇后"
	var npc_name: String = npc_data.get("name", "???")
	var title: String = profile.get("title", "")
	if title.is_empty():
		_title_label.text = npc_name
	else:
		_title_label.text = "%s - %s" % [npc_name, title]

	# Subtitle: role + mood
	var mood: String = npc_data.get("mood", "")
	var mood_display: String = mood if not mood.is_empty() else "未知"
	_subtitle_label.text = "%s | 情绪: %s" % [title if not title.is_empty() else npc_name, mood_display]

	# Portrait — try HD portrait, then fallback
	_portrait_rect.texture = null
	var portrait_path := "res://resources/art/characters/portraits/%s_portrait.png" % current_npc_id
	if ResourceLoader.exists(portrait_path):
		_portrait_rect.texture = load(portrait_path)
	else:
		# Try alternate naming
		var alt_path := "res://resources/art/characters/%s.png" % current_npc_id
		if ResourceLoader.exists(alt_path):
			_portrait_rect.texture = load(alt_path)

	# Energy
	var energy: int = npc_data.get("energy", 0)
	_energy_bar.value = energy
	if energy > 60:
		_energy_bar.modulate = Color(0.3, 0.8, 0.64)
	elif energy > 30:
		_energy_bar.modulate = Color(0.96, 0.65, 0.14)
	else:
		_energy_bar.modulate = Color(0.91, 0.27, 0.38)

	# Mood under portrait
	_mood_label.text = "情绪: %s | 体力: %d" % [mood_display, energy]

	# Personality
	var personality: String = profile.get("personality", "")
	if personality.is_empty():
		_personality_label.text = "[color=#8888a0]暂无信息[/color]"
	else:
		_personality_label.text = "[color=#e0e0e8]%s[/color]" % personality

	# Speech style
	var speech_style: String = profile.get("speech_style", "")
	if speech_style.is_empty():
		_speech_style_label.text = ""
		_speech_style_label.visible = false
	else:
		_speech_style_label.text = "语言风格: %s" % speech_style
		_speech_style_label.visible = true

	# Goal
	var goal: String = npc_data.get("goal", "")
	if goal.is_empty():
		_goal_label.text = "目标: 无"
	else:
		_goal_label.text = "目标: %s" % goal

	# Plan steps
	_clear_children(_plan_list)
	var plan = npc_data.get("plan", [])
	if plan is Array and plan.size() > 0:
		for i in range(plan.size()):
			var step_label := Label.new()
			var prefix: String = "→" if i == 0 else "○"
			step_label.text = "  %s %s" % [prefix, str(plan[i])]
			step_label.add_theme_font_size_override("font_size", 12)
			if i == 0:
				step_label.add_theme_color_override("font_color", Color("#4ecca3"))
			else:
				step_label.add_theme_color_override("font_color", Color("#8888a0"))
			step_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			_plan_list.add_child(step_label)
	else:
		var empty_label := Label.new()
		empty_label.text = "  暂无计划"
		empty_label.add_theme_font_size_override("font_size", 12)
		empty_label.add_theme_color_override("font_color", Color("#8888a0"))
		_plan_list.add_child(empty_label)

	# Relationships
	_clear_children(_relationships_container)
	var relationships = profile.get("relationships", {})
	if relationships is Dictionary and not relationships.is_empty():
		for rel_id in relationships:
			var rel_name: String = _resolve_npc_name(rel_id)
			var rel_desc: String = str(relationships[rel_id])
			var rel_row := HBoxContainer.new()
			rel_row.add_theme_constant_override("separation", 4)

			var name_lbl := Label.new()
			name_lbl.text = "  %s" % rel_name
			name_lbl.add_theme_font_size_override("font_size", 13)
			name_lbl.add_theme_color_override("font_color", Color("#4ecca3"))
			name_lbl.custom_minimum_size.x = 60
			rel_row.add_child(name_lbl)

			var arrow_lbl := Label.new()
			arrow_lbl.text = "←"
			arrow_lbl.add_theme_font_size_override("font_size", 13)
			arrow_lbl.add_theme_color_override("font_color", Color("#8888a0"))
			rel_row.add_child(arrow_lbl)

			var desc_lbl := Label.new()
			desc_lbl.text = rel_desc
			desc_lbl.add_theme_font_size_override("font_size", 13)
			desc_lbl.add_theme_color_override("font_color", Color("#8888a0"))
			desc_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			desc_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			rel_row.add_child(desc_lbl)

			_relationships_container.add_child(rel_row)
	else:
		var empty_rel := Label.new()
		empty_rel.text = "  暂无关系信息"
		empty_rel.add_theme_font_size_override("font_size", 12)
		empty_rel.add_theme_color_override("font_color", Color("#8888a0"))
		_relationships_container.add_child(empty_rel)

	# Worldview / backstory
	var backstory: String = profile.get("backstory", "")
	if backstory.is_empty():
		_worldview_label.text = "[color=#8888a0]暂无世界观信息[/color]"
	else:
		_worldview_label.text = "[color=#8888a0]%s[/color]" % backstory

	# Inventory
	_clear_children(_inventory_container)
	var inv = npc_data.get("inventory", {})
	if inv is Dictionary and not inv.is_empty():
		var has_items := false
		# Use GameState.ITEM_NAMES for proper display order/names
		for item_key in GameState.ITEM_NAMES:
			var count := int(inv.get(item_key, 0))
			if count > 0:
				has_items = true
				var item_label := Label.new()
				item_label.text = "%s×%d" % [GameState.ITEM_NAMES[item_key], count]
				item_label.add_theme_font_size_override("font_size", 13)
				_inventory_container.add_child(item_label)
		# Gold
		var gold := int(inv.get("gold", 0))
		if gold > 0:
			has_items = true
			var gold_label := Label.new()
			gold_label.text = "金币×%d" % gold
			gold_label.add_theme_font_size_override("font_size", 13)
			gold_label.add_theme_color_override("font_color", Color("#f5a623"))
			_inventory_container.add_child(gold_label)
		if not has_items:
			var empty_inv := Label.new()
			empty_inv.text = "空"
			empty_inv.add_theme_font_size_override("font_size", 12)
			empty_inv.add_theme_color_override("font_color", Color("#8888a0"))
			_inventory_container.add_child(empty_inv)
	else:
		var empty_inv := Label.new()
		empty_inv.text = "空"
		empty_inv.add_theme_font_size_override("font_size", 12)
		empty_inv.add_theme_color_override("font_color", Color("#8888a0"))
		_inventory_container.add_child(empty_inv)

	# Update button states based on player proximity
	_update_interaction_buttons(npc_data)

	visible = true


## Refresh data for the currently displayed NPC (call on world_state_updated).
func refresh() -> void:
	if current_npc_id.is_empty() or not visible:
		return
	for npc in GameState.npcs:
		if npc is Dictionary and npc.get("id", "") == current_npc_id:
			show_character(npc)
			return
	# NPC no longer exists in data — close
	_on_close()


func _on_close() -> void:
	visible = false
	current_npc_id = ""
	close_requested.emit()


# ── Helpers ──

func _update_interaction_buttons(npc_data: Dictionary) -> void:
	var player := GameState.player
	if player.is_empty():
		_talk_button.disabled = true
		_trade_button.disabled = true
		return

	var px: int = player.get("x", 0)
	var py: int = player.get("y", 0)
	var nx: int = npc_data.get("x", 0)
	var ny: int = npc_data.get("y", 0)
	var dist: int = abs(nx - px) + abs(ny - py)

	# Talk: within vision range (2)
	_talk_button.disabled = dist > 2
	_talk_button.tooltip_text = "" if dist <= 2 else "距离太远 (距离:%d)" % dist

	# Trade: adjacent (1)
	_trade_button.disabled = dist > 1
	_trade_button.tooltip_text = "" if dist <= 1 else "需要相邻才能交易 (距离:%d)" % dist


func _resolve_npc_name(npc_id: String) -> String:
	## Look up NPC display name from GameState.npcs by id.
	for npc in GameState.npcs:
		if npc is Dictionary and npc.get("id", "") == npc_id:
			return npc.get("name", npc_id)
	# Fallback: use the id itself
	return npc_id


static func _safe_dict(data: Dictionary, key: String) -> Dictionary:
	## Safely extract a Dictionary value, returning empty dict on type mismatch.
	var val = data.get(key, {})
	if val is Dictionary:
		return val
	return {}


static func _clear_children(node: Node) -> void:
	for child in node.get_children():
		child.queue_free()


func _unhandled_input(event: InputEvent) -> void:
	if not visible:
		return
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_ESCAPE:
			_on_close()
			get_viewport().set_input_as_handled()
