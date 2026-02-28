class_name NPCListPanel
extends ScrollContainer
## NPC list sorted by distance, with expandable detail cards, mood icons, energy bars,
## avatars, relationship hints, and interaction buttons.

signal talk_requested(npc_id: String, npc_name: String)
signal trade_requested(npc_id: String)
signal detail_requested(npc_id: String)

var _container: VBoxContainer
var _expanded_ids: Dictionary = {}  # npc_id -> bool

# Caches
var _mood_cache: Dictionary = {}   # mood_name -> Texture2D
var _icon_cache: Dictionary = {}   # item_key -> Texture2D
var _avatar_cache: Dictionary = {} # npc_id_suffix -> Texture2D


func _ready() -> void:
	size_flags_vertical = Control.SIZE_EXPAND_FILL
	size_flags_horizontal = Control.SIZE_EXPAND_FILL

	_container = VBoxContainer.new()
	_container.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_container.add_theme_constant_override("separation", 4)
	add_child(_container)

	_preload_assets()


func update_list(npcs: Array, player: Dictionary) -> void:
	for child in _container.get_children():
		child.queue_free()

	if player.is_empty():
		return

	var px: int = player.get("x", 0)
	var py: int = player.get("y", 0)

	var sorted_npcs := npcs.duplicate()
	sorted_npcs.sort_custom(func(a, b):
		var da = abs(a.get("x", 0) - px) + abs(a.get("y", 0) - py)
		var db = abs(b.get("x", 0) - px) + abs(b.get("y", 0) - py)
		return da < db
	)

	for npc in sorted_npcs:
		if not npc is Dictionary:
			continue
		_build_npc_card(npc, px, py, player)


func _build_npc_card(npc: Dictionary, px: int, py: int, player: Dictionary) -> void:
	var npc_id: String = npc.get("id", "")
	var npc_name: String = npc.get("name", "???")
	var dist: int = abs(npc.get("x", 0) - px) + abs(npc.get("y", 0) - py)
	var is_nearby := dist <= 2
	var is_adjacent := dist <= 1
	var npc_energy: int = npc.get("energy", 0)
	var action_str: String = npc.get("last_action", "")
	var is_processing: bool = npc.get("is_processing", false)
	var pending: int = npc.get("pending_proposals", 0)
	var color_hex: String = npc.get("color", "#4ecca3")
	var mood: String = npc.get("mood", "neutral")
	var last_action_result: String = npc.get("last_action_result", "")

	# Card panel with styled background
	var panel := PanelContainer.new()
	var panel_style := StyleBoxFlat.new()
	panel_style.bg_color = Color("#14141eea")
	panel_style.border_color = Color("#2a2a3e")
	panel_style.set_border_width_all(1)
	panel_style.set_corner_radius_all(6)
	panel_style.content_margin_left = 8
	panel_style.content_margin_right = 8
	panel_style.content_margin_top = 6
	panel_style.content_margin_bottom = 6
	if is_nearby:
		panel_style.border_color = Color(color_hex)
	panel.add_theme_stylebox_override("panel", panel_style)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 3)
	panel.add_child(vbox)

	# ── Header row: avatar + mood + name + title + distance + indicators ──
	var header_row := HBoxContainer.new()
	header_row.add_theme_constant_override("separation", 6)
	vbox.add_child(header_row)

	# Avatar (24x24, from sprite sheet first 32x32 frame)
	var avatar := _make_avatar(npc_id)
	if avatar:
		header_row.add_child(avatar)

	# Mood icon
	if _mood_cache.has(mood):
		var mood_rect := TextureRect.new()
		mood_rect.texture = _mood_cache[mood]
		mood_rect.custom_minimum_size = Vector2(16, 16)
		mood_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		mood_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		header_row.add_child(mood_rect)

	# Color dot
	var dot := Label.new()
	dot.text = "●"
	dot.add_theme_color_override("font_color", Color.from_string(color_hex, Color.WHITE))
	header_row.add_child(dot)

	# Name + title
	var name_lbl := Label.new()
	var title: String = npc.get("profile", {}).get("title", "") if npc.has("profile") and npc["profile"] is Dictionary else ""
	name_lbl.text = npc_name + ("  [%s]" % title if not title.is_empty() else "")
	if is_nearby:
		name_lbl.add_theme_color_override("font_color", Color("#4ecca3"))
	else:
		name_lbl.add_theme_color_override("font_color", Color("#8888a0"))
	name_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header_row.add_child(name_lbl)

	# Distance
	var dist_lbl := Label.new()
	dist_lbl.text = "距:%d" % dist
	dist_lbl.add_theme_font_size_override("font_size", 12)
	dist_lbl.add_theme_color_override("font_color", Color("#8888a0"))
	header_row.add_child(dist_lbl)

	# Processing indicator
	if is_processing:
		var proc := Label.new()
		proc.text = "⟳"
		proc.add_theme_color_override("font_color", Color("#4ecca3"))
		header_row.add_child(proc)

	# Proposal badge
	if pending > 0:
		var badge := Label.new()
		badge.text = "(%d)" % pending
		badge.add_theme_color_override("font_color", Color("#e94560"))
		header_row.add_child(badge)

	# ── Info row: energy bar + action + equipment + bag ──
	var info_row := HBoxContainer.new()
	info_row.add_theme_constant_override("separation", 8)
	vbox.add_child(info_row)

	# Compact energy bar (80x8)
	var energy_container := VBoxContainer.new()
	energy_container.add_theme_constant_override("separation", 1)

	var energy_bar := ProgressBar.new()
	energy_bar.max_value = 100
	energy_bar.value = npc_energy
	energy_bar.show_percentage = false
	energy_bar.custom_minimum_size = Vector2(80, 8)

	var bar_bg := StyleBoxFlat.new()
	bar_bg.bg_color = Color("#1a1a2e")
	bar_bg.set_corner_radius_all(2)
	energy_bar.add_theme_stylebox_override("background", bar_bg)

	var bar_fill := StyleBoxFlat.new()
	bar_fill.set_corner_radius_all(2)
	if npc_energy > 60:
		bar_fill.bg_color = Color("#4ecca3")
	elif npc_energy > 30:
		bar_fill.bg_color = Color("#f5a623")
	else:
		bar_fill.bg_color = Color("#e94560")
	energy_bar.add_theme_stylebox_override("fill", bar_fill)
	energy_container.add_child(energy_bar)

	var energy_lbl := Label.new()
	energy_lbl.text = "%d" % npc_energy
	energy_lbl.add_theme_font_size_override("font_size", 10)
	energy_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	if npc_energy > 60:
		energy_lbl.add_theme_color_override("font_color", Color("#4ecca3"))
	elif npc_energy > 30:
		energy_lbl.add_theme_color_override("font_color", Color("#f5a623"))
	else:
		energy_lbl.add_theme_color_override("font_color", Color("#e94560"))
	energy_container.add_child(energy_lbl)
	info_row.add_child(energy_container)

	# Action text
	var act_lbl := Label.new()
	act_lbl.text = action_str
	act_lbl.add_theme_font_size_override("font_size", 12)
	act_lbl.add_theme_color_override("font_color", Color("#8888a0"))
	act_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	info_row.add_child(act_lbl)

	# Equipment
	var equipped = npc.get("equipped")
	if equipped != null and equipped is String and not (equipped as String).is_empty():
		var eq_lbl := Label.new()
		eq_lbl.text = "⚔%s" % GameState.ITEM_NAMES.get(equipped, equipped)
		eq_lbl.add_theme_font_size_override("font_size", 12)
		info_row.add_child(eq_lbl)

	# Bag count
	var inv_count: int = npc.get("inv_count", 0)
	var inv_max: int = npc.get("inv_max", 20)
	var bag_lbl := Label.new()
	bag_lbl.text = "包:%d/%d" % [inv_count, inv_max]
	bag_lbl.add_theme_font_size_override("font_size", 12)
	bag_lbl.add_theme_color_override("font_color", Color("#8888a0"))
	info_row.add_child(bag_lbl)

	# ── Last action result ──
	if not last_action_result.is_empty():
		var result_lbl := Label.new()
		result_lbl.text = "▸ %s" % last_action_result
		result_lbl.add_theme_font_size_override("font_size", 11)
		result_lbl.add_theme_color_override("font_color", Color("#8888a0"))
		result_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		vbox.add_child(result_lbl)

	# ── Relationship hint ──
	var profile = npc.get("profile", {})
	if profile is Dictionary:
		var relationships = profile.get("relationships", {})
		if relationships is Dictionary:
			var player_id: String = player.get("id", "player")
			var player_name: String = player.get("name", "玩家")
			# Check by id or name
			var rel_text := ""
			if relationships.has(player_id):
				rel_text = str(relationships[player_id])
			elif relationships.has(player_name):
				rel_text = str(relationships[player_name])
			if not rel_text.is_empty():
				var rel_lbl := Label.new()
				rel_lbl.text = "♥ 对你: %s" % rel_text
				rel_lbl.add_theme_font_size_override("font_size", 11)
				rel_lbl.add_theme_color_override("font_color", Color("#9c27b0"))
				rel_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
				vbox.add_child(rel_lbl)

	# ── Goal ──
	var goal: String = npc.get("goal", "")
	if not goal.is_empty():
		var goal_lbl := Label.new()
		goal_lbl.text = "目标: %s" % goal
		goal_lbl.add_theme_font_size_override("font_size", 12)
		goal_lbl.add_theme_color_override("font_color", Color("#c8a832"))
		goal_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		vbox.add_child(goal_lbl)

	# ── Last message ──
	var msg: String = npc.get("last_message", "")
	if not msg.is_empty():
		var msg_lbl := Label.new()
		msg_lbl.text = "「%s」" % msg
		msg_lbl.add_theme_font_size_override("font_size", 12)
		msg_lbl.add_theme_color_override("font_color", Color("#8888a0"))
		msg_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		vbox.add_child(msg_lbl)

	# ── Thought ──
	var thought: String = npc.get("thought", "")
	if not thought.is_empty():
		var thought_lbl := Label.new()
		thought_lbl.text = "思考: %s" % thought
		thought_lbl.add_theme_font_size_override("font_size", 11)
		thought_lbl.add_theme_color_override("font_color", Color("#8888a0"))
		thought_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		vbox.add_child(thought_lbl)

	# ── Action buttons ──
	var btn_row := HBoxContainer.new()
	btn_row.add_theme_constant_override("separation", 4)
	vbox.add_child(btn_row)

	if is_nearby:
		var talk_btn := Button.new()
		talk_btn.text = "说话"
		talk_btn.pressed.connect(func(): talk_requested.emit(npc_id, npc_name))
		btn_row.add_child(talk_btn)

	if is_adjacent:
		var trade_btn := Button.new()
		trade_btn.text = "交易"
		trade_btn.pressed.connect(func(): trade_requested.emit(npc_id))
		btn_row.add_child(trade_btn)

	# Detail button (always visible)
	var detail_btn := Button.new()
	detail_btn.text = "详情"
	detail_btn.add_theme_font_size_override("font_size", 11)
	var _npc_id: String = npc_id
	detail_btn.pressed.connect(func(): detail_requested.emit(_npc_id))
	btn_row.add_child(detail_btn)

	# Expand/collapse button
	var expand_btn := Button.new()
	var is_expanded: bool = _expanded_ids.get(npc_id, false)
	expand_btn.text = "▲ 收起" if is_expanded else "▼ 展开"
	expand_btn.add_theme_font_size_override("font_size", 11)
	btn_row.add_child(expand_btn)

	# Detail section (expandable)
	var detail := VBoxContainer.new()
	detail.visible = is_expanded
	detail.add_theme_constant_override("separation", 2)
	vbox.add_child(detail)

	expand_btn.pressed.connect(func():
		_expanded_ids[npc_id] = not _expanded_ids.get(npc_id, false)
		detail.visible = _expanded_ids[npc_id]
		expand_btn.text = "▲ 收起" if _expanded_ids[npc_id] else "▼ 展开"
	)

	_build_detail_section(detail, npc)

	_container.add_child(panel)


func _build_detail_section(container: VBoxContainer, npc: Dictionary) -> void:
	var profile = npc.get("profile", {})
	if not (profile is Dictionary):
		profile = {}

	var sep := HSeparator.new()
	sep.add_theme_color_override("separator", Color("#2a2a3e"))
	container.add_child(sep)

	# Personality
	var personality: String = profile.get("personality", npc.get("personality", ""))
	if not personality.is_empty():
		var lbl := Label.new()
		lbl.text = "性格: %s" % personality
		lbl.add_theme_font_size_override("font_size", 12)
		lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		container.add_child(lbl)

	# Backstory
	var backstory: String = profile.get("backstory", "")
	if not backstory.is_empty():
		var lbl := Label.new()
		lbl.text = "背景: %s" % backstory
		lbl.add_theme_font_size_override("font_size", 12)
		lbl.add_theme_color_override("font_color", Color("#8888a0"))
		lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		container.add_child(lbl)

	# Goals
	var goals = profile.get("goals", [])
	if goals is Array and goals.size() > 0:
		var goals_lbl := Label.new()
		goals_lbl.text = "目标:"
		goals_lbl.add_theme_font_size_override("font_size", 12)
		container.add_child(goals_lbl)
		for g in goals:
			var g_lbl := Label.new()
			g_lbl.text = "  · %s" % str(g)
			g_lbl.add_theme_font_size_override("font_size", 11)
			container.add_child(g_lbl)

	# Plan steps
	var plan = npc.get("plan", [])
	if plan is Array and plan.size() > 0:
		var plan_lbl := Label.new()
		plan_lbl.text = "计划:"
		plan_lbl.add_theme_font_size_override("font_size", 12)
		container.add_child(plan_lbl)
		for step in plan:
			var s_lbl := Label.new()
			s_lbl.text = "  → %s" % str(step)
			s_lbl.add_theme_font_size_override("font_size", 11)
			s_lbl.add_theme_color_override("font_color", Color("#c8a832"))
			container.add_child(s_lbl)

	# Inventory breakdown with icons
	var inv: Dictionary = npc.get("inventory", {})
	if not inv.is_empty():
		var inv_sep := HSeparator.new()
		inv_sep.add_theme_color_override("separator", Color("#2a2a3e"))
		container.add_child(inv_sep)

		var inv_lbl := Label.new()
		inv_lbl.text = "库存:"
		inv_lbl.add_theme_font_size_override("font_size", 12)
		container.add_child(inv_lbl)

		var inv_flow := HFlowContainer.new()
		inv_flow.add_theme_constant_override("h_separation", 6)
		inv_flow.add_theme_constant_override("v_separation", 2)
		container.add_child(inv_flow)

		for key in GameState.ITEM_NAMES:
			var qty := int(inv.get(key, 0))
			if qty > 0:
				var item_row := HBoxContainer.new()
				item_row.add_theme_constant_override("separation", 2)
				var icon := _make_item_icon(key)
				if icon:
					item_row.add_child(icon)
				var i_lbl := Label.new()
				i_lbl.text = "%s:%d" % [GameState.ITEM_NAMES[key], qty]
				i_lbl.add_theme_font_size_override("font_size", 11)
				item_row.add_child(i_lbl)
				inv_flow.add_child(item_row)

		var gold := int(inv.get("gold", 0))
		if gold > 0:
			var gold_row := HBoxContainer.new()
			gold_row.add_theme_constant_override("separation", 2)
			var g_icon := _make_item_icon("gold")
			if g_icon:
				gold_row.add_child(g_icon)
			var g_lbl := Label.new()
			g_lbl.text = "金币:%d" % gold
			g_lbl.add_theme_font_size_override("font_size", 11)
			g_lbl.add_theme_color_override("font_color", Color("#c8a832"))
			gold_row.add_child(g_lbl)
			inv_flow.add_child(gold_row)


# ── Asset helpers ──

func _preload_assets() -> void:
	# Mood icons
	var moods := ["happy", "neutral", "sad", "anxious", "angry"]
	for m in moods:
		var path := "res://resources/art/ui/mood_%s.png" % m
		if ResourceLoader.exists(path):
			_mood_cache[m] = load(path)

	# Item icons
	var items := ["wood", "stone", "ore", "food", "herb", "rope",
		"potion", "tool", "bread", "gold"]
	for item in items:
		var path := "res://resources/art/icons/%s.png" % item
		if ResourceLoader.exists(path):
			_icon_cache[item] = load(path)

	# NPC avatars (try common suffixes)
	var avatar_names := ["he", "sui", "shan", "tang", "kuang", "mu",
		"lan", "shi", "shangren"]
	for a_name in avatar_names:
		var path := "res://resources/art/characters/npc_%s.png" % a_name
		if ResourceLoader.exists(path):
			_avatar_cache[a_name] = load(path)


func _make_avatar(npc_id: String) -> TextureRect:
	# Try to find avatar by matching npc_id suffix to known character names
	var tex: Texture2D = null
	for suffix in _avatar_cache:
		if npc_id.to_lower().find(suffix) >= 0:
			tex = _avatar_cache[suffix]
			break

	if tex == null:
		return null

	# Create AtlasTexture to extract first 32x32 frame from sprite sheet
	var atlas := AtlasTexture.new()
	atlas.atlas = tex
	atlas.region = Rect2(0, 0, 32, 32)

	var rect := TextureRect.new()
	rect.texture = atlas
	rect.custom_minimum_size = Vector2(24, 24)
	rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	return rect


func _make_item_icon(item_key: String) -> TextureRect:
	if not _icon_cache.has(item_key):
		return null
	var tex_rect := TextureRect.new()
	tex_rect.texture = _icon_cache[item_key]
	tex_rect.custom_minimum_size = Vector2(14, 14)
	tex_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	tex_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	return tex_rect
