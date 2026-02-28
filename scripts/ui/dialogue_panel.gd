class_name DialoguePanel
extends PanelContainer
## NPC dialogue panel — centered bottom overlay with NPC sprite preview,
## typewriter text effect, loading animation, and styled option buttons.
## Inherits dark tarot theme from UIManager.

signal reply_sent(npc_id: String, message: String)

# ── Node refs ──
var _speaker_label: Label
var _message_text: RichTextLabel
var _options_box: VBoxContainer
var _custom_input: LineEdit
var _close_button: Button
var _npc_sprite: TextureRect
var _loading_label: Label
var _content_hbox: HBoxContainer

# State
var _current_npc_id: String = ""

# Typewriter
var _typewriter_timer: Timer
var _full_message_bbcode: String = ""
var _full_message_plain: String = ""
var _char_index: int = 0
var _typewriter_active: bool = false
const TYPEWRITER_SPEED := 0.025  # seconds per character

# Loading dots animation
var _loading_timer: Timer
var _loading_dot_count: int = 0


func _ready() -> void:
	visible = false

	# Layout is controlled by game_manager (anchors, offsets).
	# We only set minimum size here.
	custom_minimum_size = Vector2(400, 180)

	# Main horizontal: sprite | content
	_content_hbox = HBoxContainer.new()
	_content_hbox.add_theme_constant_override("separation", 12)
	add_child(_content_hbox)

	# ── NPC sprite preview (left side) ──
	var sprite_container := CenterContainer.new()
	sprite_container.custom_minimum_size = Vector2(64, 0)
	_content_hbox.add_child(sprite_container)

	_npc_sprite = TextureRect.new()
	_npc_sprite.custom_minimum_size = Vector2(56, 56)
	_npc_sprite.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_npc_sprite.expand_mode = TextureRect.EXPAND_FIT_WIDTH_PROPORTIONAL
	sprite_container.add_child(_npc_sprite)

	# ── Right side: speaker, message, options, input ──
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 6)
	vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_content_hbox.add_child(vbox)

	# Header row: speaker name + close button
	var header := HBoxContainer.new()
	vbox.add_child(header)

	_speaker_label = Label.new()
	_speaker_label.text = "NPC 说:"
	_speaker_label.add_theme_font_size_override("font_size", 16)
	_speaker_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(_speaker_label)

	_close_button = Button.new()
	_close_button.text = "✕"
	_close_button.custom_minimum_size = Vector2(28, 28)
	_close_button.pressed.connect(hide_dialogue)
	header.add_child(_close_button)

	# Separator
	vbox.add_child(HSeparator.new())

	# Message text with typewriter
	_message_text = RichTextLabel.new()
	_message_text.bbcode_enabled = true
	_message_text.fit_content = true
	_message_text.custom_minimum_size.y = 40
	_message_text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	vbox.add_child(_message_text)

	# Options container
	_options_box = VBoxContainer.new()
	_options_box.add_theme_constant_override("separation", 4)
	vbox.add_child(_options_box)

	# Custom input row
	var input_row := HBoxContainer.new()
	input_row.add_theme_constant_override("separation", 4)
	vbox.add_child(input_row)

	_custom_input = LineEdit.new()
	_custom_input.placeholder_text = "自定义回复..."
	_custom_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_custom_input.text_submitted.connect(func(_t): _send_custom())
	input_row.add_child(_custom_input)

	var send_btn := Button.new()
	send_btn.text = "发送"
	send_btn.custom_minimum_size.x = 56
	send_btn.pressed.connect(_send_custom)
	input_row.add_child(send_btn)

	# ── Typewriter timer ──
	_typewriter_timer = Timer.new()
	_typewriter_timer.wait_time = TYPEWRITER_SPEED
	_typewriter_timer.one_shot = false
	_typewriter_timer.timeout.connect(_on_typewriter_tick)
	add_child(_typewriter_timer)

	# ── Loading dots timer ──
	_loading_timer = Timer.new()
	_loading_timer.wait_time = 0.4
	_loading_timer.one_shot = false
	_loading_timer.timeout.connect(_on_loading_tick)
	add_child(_loading_timer)


# ── Public API (kept compatible) ──

func show_dialogue(dialogue: Dictionary) -> void:
	_current_npc_id = dialogue.get("from_id", "")
	var from_name: String = dialogue.get("from_name", "NPC")
	var npc_color: String = _get_npc_color(_current_npc_id)

	# Speaker name in NPC color
	_speaker_label.text = "%s 说:" % from_name
	_speaker_label.add_theme_color_override("font_color", Color.from_string(npc_color, Color("#4ecca3")))

	# Load NPC sprite
	_load_npc_sprite(_current_npc_id)

	# Start typewriter for message
	var msg: String = dialogue.get("message", "")
	_start_typewriter(msg)

	# Clear old options
	for child in _options_box.get_children():
		child.queue_free()

	# Build option buttons or show loading
	var opts = dialogue.get("reply_options")
	if opts != null and opts is Array and opts.size() > 0:
		_loading_timer.stop()
		var labels := ["A", "B", "C", "D"]
		for i in opts.size():
			var btn := Button.new()
			var prefix: String = labels[i] if i < labels.size() else str(i + 1)
			btn.text = "[%s] %s" % [prefix, opts[i]]
			btn.alignment = HORIZONTAL_ALIGNMENT_LEFT
			# Gold accent for option buttons
			btn.add_theme_color_override("font_color", Color("#c8a832"))
			btn.add_theme_color_override("font_hover_color", Color("#e0e0e8"))
			var opt_text: String = opts[i]
			btn.pressed.connect(func(): _send_reply(opt_text))
			_options_box.add_child(btn)
	else:
		# Loading state: "正在思考..." with animated dots
		_loading_label = Label.new()
		_loading_label.text = "正在思考..."
		_loading_label.add_theme_color_override("font_color", Color("#8888a0"))
		_loading_label.add_theme_font_size_override("font_size", 13)
		_options_box.add_child(_loading_label)
		_loading_dot_count = 0
		_loading_timer.start()

	_custom_input.text = ""
	visible = true


func hide_dialogue() -> void:
	visible = false
	_current_npc_id = ""
	_stop_typewriter()
	_loading_timer.stop()


# ── Internals ──

func _send_reply(msg: String) -> void:
	if _current_npc_id.is_empty():
		return
	reply_sent.emit(_current_npc_id, msg)
	hide_dialogue()


func _send_custom() -> void:
	var msg := _custom_input.text.strip_edges()
	if not msg.is_empty():
		_send_reply(msg)


func _get_npc_color(npc_id: String) -> String:
	# Look up NPC color from GameState.npcs array
	for npc in GameState.npcs:
		if npc is Dictionary:
			var id: String = npc.get("id", npc.get("npc_id", ""))
			if id == npc_id:
				return npc.get("color", "#4ecca3")
	return "#4ecca3"


func _load_npc_sprite(npc_id: String) -> void:
	# Try to load character sprite from resources/art/characters/
	# NPC IDs typically map to file names like "npc_he", "npc_sui", etc.
	var path := "res://resources/art/characters/%s.png" % npc_id
	if ResourceLoader.exists(path):
		_npc_sprite.texture = load(path)
		_npc_sprite.visible = true
	else:
		# Try without npc_ prefix
		var alt_path := "res://resources/art/characters/npc_%s.png" % npc_id
		if ResourceLoader.exists(alt_path):
			_npc_sprite.texture = load(alt_path)
			_npc_sprite.visible = true
		else:
			_npc_sprite.visible = false


# ── Typewriter Effect ──

func _start_typewriter(msg: String) -> void:
	_stop_typewriter()
	_full_message_bbcode = "[color=#4ecca3]%s[/color]" % msg
	_full_message_plain = msg
	_char_index = 0
	_message_text.text = ""

	if msg.is_empty():
		return

	_typewriter_active = true
	_typewriter_timer.start()


func _stop_typewriter() -> void:
	_typewriter_active = false
	_typewriter_timer.stop()


func _on_typewriter_tick() -> void:
	if not _typewriter_active:
		_typewriter_timer.stop()
		return

	_char_index += 1
	if _char_index >= _full_message_plain.length():
		# Finished — show full message
		_message_text.text = ""
		_message_text.append_text(_full_message_bbcode)
		_stop_typewriter()
	else:
		# Show partial text
		var partial: String = _full_message_plain.substr(0, _char_index)
		_message_text.text = ""
		_message_text.append_text("[color=#4ecca3]%s[/color]" % partial)


func _input(event: InputEvent) -> void:
	# Click or key press skips typewriter to show full text
	if _typewriter_active and visible:
		if event is InputEventMouseButton and event.pressed:
			_skip_typewriter()
		elif event is InputEventKey and event.pressed and event.keycode == KEY_SPACE:
			_skip_typewriter()


func _skip_typewriter() -> void:
	if _typewriter_active:
		_message_text.text = ""
		_message_text.append_text(_full_message_bbcode)
		_stop_typewriter()


# ── Loading Dots Animation ──

func _on_loading_tick() -> void:
	_loading_dot_count = (_loading_dot_count + 1) % 4
	if is_instance_valid(_loading_label):
		var dots := ".".repeat(_loading_dot_count)
		_loading_label.text = "正在思考%s" % dots
