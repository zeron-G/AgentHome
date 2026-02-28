class_name StatusPanel
extends VBoxContainer
## Player status: energy, equipment, gold, inventory with icons, craft/equip/build actions.
## Enhanced with item icons, mood display, last_action_result, and HFlowContainer inventory grid.

signal action_requested(action: Dictionary)

# Icon cache: item_key -> Texture2D
var _icon_cache: Dictionary = {}
var _mood_cache: Dictionary = {}

# Header
var _name_label: Label
var _mood_icon: TextureRect

# Energy
var _energy_bar: ProgressBar
var _energy_label: Label
var _action_result_label: Label

# Equipment
var _equipped_label: Label
var _equip_btn: Button
var _unequip_btn: Button
var _gold_label: Label

# Inventory
var _inv_title: Label
var _inv_flow: HFlowContainer

# Craft / Build
var _craft_box: VBoxContainer
var _build_box: VBoxContainer
var _craft_toggle: Button
var _build_toggle: Button
var _craft_visible: bool = false
var _build_visible: bool = false


func _ready() -> void:
	add_theme_constant_override("separation", 6)
	_preload_icons()

	# ── Header row: name + mood icon ──
	var header_row := HBoxContainer.new()
	header_row.add_theme_constant_override("separation", 6)
	add_child(header_row)

	_name_label = Label.new()
	_name_label.text = "玩家"
	_name_label.add_theme_font_size_override("font_size", 18)
	_name_label.add_theme_color_override("font_color", Color("#c8a832"))
	_name_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header_row.add_child(_name_label)

	_mood_icon = TextureRect.new()
	_mood_icon.custom_minimum_size = Vector2(20, 20)
	_mood_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_mood_icon.visible = false
	header_row.add_child(_mood_icon)

	# ── Energy bar ──
	_energy_bar = ProgressBar.new()
	_energy_bar.max_value = 100
	_energy_bar.value = 100
	_energy_bar.show_percentage = false
	_energy_bar.custom_minimum_size.y = 18
	var bar_style := StyleBoxFlat.new()
	bar_style.bg_color = Color("#1a1a2e")
	bar_style.border_color = Color("#2a2a3e")
	bar_style.set_border_width_all(1)
	bar_style.set_corner_radius_all(3)
	_energy_bar.add_theme_stylebox_override("background", bar_style)
	add_child(_energy_bar)

	_energy_label = Label.new()
	_energy_label.text = "体力: 100 / 100"
	_energy_label.add_theme_font_size_override("font_size", 12)
	add_child(_energy_label)

	# ── Last action result ──
	_action_result_label = Label.new()
	_action_result_label.text = ""
	_action_result_label.add_theme_font_size_override("font_size", 11)
	_action_result_label.add_theme_color_override("font_color", Color("#8888a0"))
	_action_result_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_action_result_label.visible = false
	add_child(_action_result_label)

	# ── Equipment row ──
	_equipped_label = Label.new()
	_equipped_label.text = "装备: 无"
	_equipped_label.add_theme_font_size_override("font_size", 13)
	add_child(_equipped_label)

	var equip_row := HBoxContainer.new()
	equip_row.add_theme_constant_override("separation", 4)
	add_child(equip_row)

	_equip_btn = Button.new()
	_equip_btn.text = "装备工具"
	_equip_btn.pressed.connect(func(): _show_equip_menu())
	equip_row.add_child(_equip_btn)

	_unequip_btn = Button.new()
	_unequip_btn.text = "卸下"
	_unequip_btn.visible = false
	_unequip_btn.pressed.connect(func(): action_requested.emit({"action": "unequip"}))
	equip_row.add_child(_unequip_btn)

	# ── Gold row with icon ──
	var gold_row := HBoxContainer.new()
	gold_row.add_theme_constant_override("separation", 4)
	add_child(gold_row)

	var gold_icon := _make_item_icon("gold")
	if gold_icon:
		gold_row.add_child(gold_icon)

	_gold_label = Label.new()
	_gold_label.text = "金币: 0"
	_gold_label.add_theme_color_override("font_color", Color("#c8a832"))
	gold_row.add_child(_gold_label)

	add_child(_make_separator())

	# ── Inventory ──
	_inv_title = Label.new()
	_inv_title.text = "背包 (0/20)"
	_inv_title.add_theme_font_size_override("font_size", 14)
	_inv_title.add_theme_color_override("font_color", Color("#e0e0e8"))
	add_child(_inv_title)

	var inv_scroll := ScrollContainer.new()
	inv_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	inv_scroll.custom_minimum_size.y = 90
	add_child(inv_scroll)

	_inv_flow = HFlowContainer.new()
	_inv_flow.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_inv_flow.add_theme_constant_override("h_separation", 6)
	_inv_flow.add_theme_constant_override("v_separation", 4)
	inv_scroll.add_child(_inv_flow)

	add_child(_make_separator())

	# ── Craft toggle ──
	_craft_toggle = Button.new()
	_craft_toggle.text = "合成 [C]"
	_craft_toggle.pressed.connect(_toggle_craft)
	add_child(_craft_toggle)

	_craft_box = VBoxContainer.new()
	_craft_box.visible = false
	_craft_box.add_theme_constant_override("separation", 4)
	add_child(_craft_box)

	# ── Build toggle ──
	_build_toggle = Button.new()
	_build_toggle.text = "建造 [B]"
	_build_toggle.pressed.connect(_toggle_build)
	add_child(_build_toggle)

	_build_box = VBoxContainer.new()
	_build_box.visible = false
	_build_box.add_theme_constant_override("separation", 4)
	add_child(_build_box)


func update_status(player: Dictionary) -> void:
	if player.is_empty():
		return

	_name_label.text = player.get("name", "玩家")

	# Mood icon
	var mood: String = player.get("mood", "")
	if not mood.is_empty() and _mood_cache.has(mood):
		_mood_icon.texture = _mood_cache[mood]
		_mood_icon.visible = true
	else:
		_mood_icon.visible = false

	# Energy bar with color gradient
	var energy: int = player.get("energy", 100)
	_energy_bar.value = energy
	_energy_label.text = "体力: %d / 100" % energy

	var fill_style := StyleBoxFlat.new()
	fill_style.set_corner_radius_all(3)
	if energy > 60:
		fill_style.bg_color = Color("#4ecca3")
		_energy_bar.modulate = Color.WHITE
	elif energy > 30:
		fill_style.bg_color = Color("#f5a623")
		_energy_bar.modulate = Color.WHITE
	else:
		fill_style.bg_color = Color("#e94560")
		_energy_bar.modulate = Color.WHITE
	_energy_bar.add_theme_stylebox_override("fill", fill_style)

	# Last action result
	var action_result: String = player.get("last_action_result", "")
	if not action_result.is_empty():
		_action_result_label.text = action_result
		_action_result_label.visible = true
	else:
		_action_result_label.visible = false

	# Equipment
	var equipped = player.get("equipped")
	if equipped != null and equipped is String and not (equipped as String).is_empty():
		_equipped_label.text = "装备: %s" % GameState.ITEM_NAMES.get(equipped, equipped)
		_unequip_btn.visible = true
	else:
		_equipped_label.text = "装备: 无"
		_unequip_btn.visible = false

	# Gold
	var inv: Dictionary = player.get("inventory", {})
	_gold_label.text = "金币: %d" % int(inv.get("gold", 0))

	# Inventory count
	var total := 0
	for key in GameState.ITEM_NAMES:
		total += int(inv.get(key, 0))
	_inv_title.text = "背包 (%d/20)" % total

	# Rebuild inventory flow grid
	for child in _inv_flow.get_children():
		child.queue_free()
	for key in GameState.ITEM_NAMES:
		var qty := int(inv.get(key, 0))
		if qty > 0:
			var item_card := _make_inventory_card(key, qty)
			_inv_flow.add_child(item_card)

	# Update craft & build
	_rebuild_craft_box(inv)
	_rebuild_build_box(inv)


func _toggle_craft() -> void:
	_craft_visible = not _craft_visible
	_craft_box.visible = _craft_visible
	_craft_toggle.text = "合成 [C] ▲" if _craft_visible else "合成 [C]"


func _toggle_build() -> void:
	_build_visible = not _build_visible
	_build_box.visible = _build_visible
	_build_toggle.text = "建造 [B] ▲" if _build_visible else "建造 [B]"


func _make_inventory_card(item_key: String, qty: int) -> PanelContainer:
	var panel := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = Color("#1a1a2e")
	style.border_color = Color("#2a2a3e")
	style.set_border_width_all(1)
	style.set_corner_radius_all(4)
	style.content_margin_left = 4
	style.content_margin_right = 4
	style.content_margin_top = 2
	style.content_margin_bottom = 2
	panel.add_theme_stylebox_override("panel", style)

	var hbox := HBoxContainer.new()
	hbox.add_theme_constant_override("separation", 3)
	panel.add_child(hbox)

	# Item icon
	var icon := _make_item_icon(item_key)
	if icon:
		hbox.add_child(icon)

	# Name + qty
	var lbl := Label.new()
	lbl.text = "%s ×%d" % [GameState.ITEM_NAMES.get(item_key, item_key), qty]
	lbl.add_theme_font_size_override("font_size", 12)
	hbox.add_child(lbl)

	# Action button for consumables / equippables
	if item_key in ["potion", "bread"]:
		var use_btn := Button.new()
		use_btn.text = "用"
		use_btn.custom_minimum_size.x = 30
		use_btn.add_theme_font_size_override("font_size", 11)
		var k: String = item_key
		use_btn.pressed.connect(func(): action_requested.emit(
			{"action": "use_item", "use_item": k}))
		hbox.add_child(use_btn)
	elif item_key in ["tool", "rope"]:
		var eq_btn := Button.new()
		eq_btn.text = "装"
		eq_btn.custom_minimum_size.x = 30
		eq_btn.add_theme_font_size_override("font_size", 11)
		var k: String = item_key
		eq_btn.pressed.connect(func(): action_requested.emit(
			{"action": "use_item", "use_item": k}))
		hbox.add_child(eq_btn)

	return panel


func _rebuild_craft_box(inv: Dictionary) -> void:
	for child in _craft_box.get_children():
		child.queue_free()

	for recipe_key in GameState.CRAFTING_RECIPES:
		var mats: Dictionary = GameState.CRAFTING_RECIPES[recipe_key]
		var can_craft := true
		for mat in mats:
			if int(inv.get(mat, 0)) < mats[mat]:
				can_craft = false
				break

		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 4)

		# Output icon
		var out_icon := _make_item_icon(recipe_key)
		if out_icon:
			row.add_child(out_icon)

		# Craft button
		var btn := Button.new()
		var item_name: String = GameState.ITEM_NAMES.get(recipe_key, recipe_key)
		btn.text = item_name
		btn.disabled = not can_craft
		btn.custom_minimum_size.x = 56
		var craft_key: String = recipe_key
		btn.pressed.connect(func(): action_requested.emit(
			{"action": "craft", "craft_item": craft_key}))
		row.add_child(btn)

		# Arrow
		var arrow_lbl := Label.new()
		arrow_lbl.text = " ← "
		arrow_lbl.add_theme_font_size_override("font_size", 12)
		arrow_lbl.add_theme_color_override("font_color", Color("#8888a0"))
		row.add_child(arrow_lbl)

		# Material icons + text
		var mat_hbox := HBoxContainer.new()
		mat_hbox.add_theme_constant_override("separation", 2)
		for mat in mats:
			var need: int = mats[mat]
			var have: int = int(inv.get(mat, 0))
			var mi := _make_item_icon(mat)
			if mi:
				mat_hbox.add_child(mi)
			var ml := Label.new()
			ml.text = "%s×%d(%d)" % [GameState.ITEM_NAMES.get(mat, mat), need, have]
			ml.add_theme_font_size_override("font_size", 11)
			if have >= need:
				ml.add_theme_color_override("font_color", Color("#4ecca3"))
			else:
				ml.add_theme_color_override("font_color", Color("#e94560"))
			mat_hbox.add_child(ml)
		row.add_child(mat_hbox)

		_craft_box.add_child(row)


func _rebuild_build_box(inv: Dictionary) -> void:
	for child in _build_box.get_children():
		child.queue_free()

	for furn_key in GameState.FURNITURE_RECIPES:
		var recipe: Dictionary = GameState.FURNITURE_RECIPES[furn_key]
		var can_build := true
		for mat in recipe:
			if mat == "effect":
				continue
			if int(inv.get(mat, 0)) < recipe[mat]:
				can_build = false
				break

		var row := VBoxContainer.new()
		row.add_theme_constant_override("separation", 1)

		var top_row := HBoxContainer.new()
		top_row.add_theme_constant_override("separation", 4)

		# Furniture icon
		var furn_icon := _make_item_icon(furn_key)
		if furn_icon:
			top_row.add_child(furn_icon)

		# Build button
		var btn := Button.new()
		var furn_names := {"bed": "床", "table": "桌子", "chair": "椅子"}
		btn.text = furn_names.get(furn_key, furn_key)
		btn.disabled = not can_build
		btn.custom_minimum_size.x = 56
		var build_key: String = furn_key
		btn.pressed.connect(func(): action_requested.emit(
			{"action": "build", "build_furniture": build_key}))
		top_row.add_child(btn)

		# Arrow
		var arrow_lbl := Label.new()
		arrow_lbl.text = " ← "
		arrow_lbl.add_theme_font_size_override("font_size", 12)
		arrow_lbl.add_theme_color_override("font_color", Color("#8888a0"))
		top_row.add_child(arrow_lbl)

		# Materials
		var mat_hbox := HBoxContainer.new()
		mat_hbox.add_theme_constant_override("separation", 2)
		for mat in recipe:
			if mat == "effect":
				continue
			var need: int = recipe[mat]
			var have: int = int(inv.get(mat, 0))
			var mi := _make_item_icon(mat)
			if mi:
				mat_hbox.add_child(mi)
			var ml := Label.new()
			ml.text = "%s×%d(%d)" % [GameState.ITEM_NAMES.get(mat, mat), need, have]
			ml.add_theme_font_size_override("font_size", 11)
			if have >= need:
				ml.add_theme_color_override("font_color", Color("#4ecca3"))
			else:
				ml.add_theme_color_override("font_color", Color("#e94560"))
			mat_hbox.add_child(ml)
		top_row.add_child(mat_hbox)
		row.add_child(top_row)

		# Effect description
		var effect_str: String = recipe.get("effect", "")
		if not effect_str.is_empty():
			var effect_lbl := Label.new()
			effect_lbl.text = "    效果: %s" % effect_str
			effect_lbl.add_theme_font_size_override("font_size", 11)
			effect_lbl.add_theme_color_override("font_color", Color("#9c27b0"))
			row.add_child(effect_lbl)

		_build_box.add_child(row)


func _show_equip_menu() -> void:
	var inv := GameState.get_player_inventory()
	var equippable := ["tool", "rope"]
	for item in equippable:
		if int(inv.get(item, 0)) > 0:
			action_requested.emit({"action": "use_item", "use_item": item})
			return


# ── Icon helpers ──

func _preload_icons() -> void:
	# Item icons
	var icon_items := ["wood", "stone", "ore", "food", "herb", "rope",
		"potion", "tool", "bread", "gold", "bed", "table", "chair"]
	for item in icon_items:
		var path := "res://resources/art/icons/%s.png" % item
		if ResourceLoader.exists(path):
			_icon_cache[item] = load(path)

	# Mood icons
	var moods := ["happy", "neutral", "sad", "anxious", "angry"]
	for m in moods:
		var path := "res://resources/art/ui/mood_%s.png" % m
		if ResourceLoader.exists(path):
			_mood_cache[m] = load(path)


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
