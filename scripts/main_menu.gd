extends Control
## Main menu — built entirely in code to avoid .tscn format issues.

var server_url_input: LineEdit
var start_button: Button
var quick_start_button: Button
var status_label: Label


func _ready() -> void:
	# Dark background
	var bg := ColorRect.new()
	bg.color = Color(0.06, 0.06, 0.1)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	# Center container
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(center)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 20)
	center.add_child(vbox)

	# Title
	var title := Label.new()
	title.text = "AgentHome"
	title.add_theme_font_size_override("font_size", 48)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(title)

	# Subtitle
	var subtitle := Label.new()
	subtitle.text = "LLM 驱动的文字冒险"
	subtitle.add_theme_font_size_override("font_size", 20)
	subtitle.add_theme_color_override("font_color", Color(0.6, 0.6, 0.7))
	subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(subtitle)

	# Spacer
	var spacer := Control.new()
	spacer.custom_minimum_size.y = 30
	vbox.add_child(spacer)

	# URL label
	var url_label := Label.new()
	url_label.text = "服务器地址:"
	vbox.add_child(url_label)

	# Server URL input
	server_url_input = LineEdit.new()
	server_url_input.text = GameState.server_url
	server_url_input.custom_minimum_size = Vector2(400, 40)
	server_url_input.text_submitted.connect(func(_t): _on_start_pressed())
	vbox.add_child(server_url_input)

	# Spacer 2
	var spacer2 := Control.new()
	spacer2.custom_minimum_size.y = 10
	vbox.add_child(spacer2)

	# Button row
	var btn_row := HBoxContainer.new()
	btn_row.add_theme_constant_override("separation", 16)
	btn_row.alignment = BoxContainer.ALIGNMENT_CENTER
	vbox.add_child(btn_row)

	# Start button
	start_button = Button.new()
	start_button.text = "开始游戏"
	start_button.custom_minimum_size = Vector2(180, 50)
	start_button.pressed.connect(_on_start_pressed)
	btn_row.add_child(start_button)

	# Quick start button
	quick_start_button = Button.new()
	quick_start_button.text = "快速开始"
	quick_start_button.custom_minimum_size = Vector2(180, 50)
	quick_start_button.pressed.connect(_on_quick_start)
	btn_row.add_child(quick_start_button)

	# Status label
	status_label = Label.new()
	status_label.text = "未连接"
	status_label.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
	status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(status_label)


func _on_start_pressed() -> void:
	var url := server_url_input.text.strip_edges()
	if url.is_empty():
		status_label.text = "请输入服务器地址"
		return
	if not url.begins_with("ws://") and not url.begins_with("wss://"):
		status_label.text = "地址需以 ws:// 或 wss:// 开头"
		return
	GameState.server_url = url
	_enter_game()


func _on_quick_start() -> void:
	GameState.server_url = "ws://localhost:8000/ws"
	_enter_game()


func _enter_game() -> void:
	status_label.text = "正在进入游戏..."
	start_button.disabled = true
	quick_start_button.disabled = true
	get_tree().change_scene_to_file("res://scenes/game.tscn")
