extends Node2D
## Game scene orchestrator (Node2D root).
## Builds the entire scene tree programmatically: world layer (TileMap, characters,
## overlays), camera, visual effects, and a CanvasLayer UI with all panels.
## Connects GameState signals and dispatches data to every subsystem each tick.

# ════════════════════════════════════════════════════════
#  Constants
# ════════════════════════════════════════════════════════

const WORLD_WIDTH: int = 20
const WORLD_HEIGHT: int = 20
const TILE_SIZE: int = 32

# ════════════════════════════════════════════════════════
#  Node references — populated in _ready()
# ════════════════════════════════════════════════════════

# WebSocket (pre-existing child in game.tscn)
var ws_client: Node

# World layer
var world_layer: Node2D
var terrain_map: TileMapController
var resource_overlay: ResourceOverlay
var furniture_overlay: FurnitureOverlay
var char_manager: CharacterManager

# Camera & effects
var game_camera: GameCamera
var weather_fx: WeatherFX
var day_night: DayNightCycle

# UI layer
var ui_layer: CanvasLayer
var ui_manager: UIManager
var header: HeaderBar
var side_panel: SidePanel
var status_panel: StatusPanel
var npc_list: NPCListPanel
var market_panel: MarketPanel
var settings_panel: SettingsPanel
var narrative: NarrativePanel
var god_panel: GodPanel
var mini_map: MiniMapPanel
var action_bar: ActionBar
var dialogue: DialoguePanel
var char_detail: CharacterDetail
var talk_input: LineEdit
var talk_send_btn: Button

# State
var _talk_target_id: String = ""
var _talk_target_name: String = ""
var zone_map := ZoneMap.new()


# ════════════════════════════════════════════════════════
#  SCENE CONSTRUCTION
# ════════════════════════════════════════════════════════

func _ready() -> void:
	ws_client = $WSClient

	_build_world_layer()
	_build_camera_and_fx()
	_build_ui_layer()
	_connect_signals()

	narrative.append_system("[color=#9c27b0]正在连接服务器...[/color]")

	# Start WebSocket connection
	ws_client.connect_to_server(GameState.server_url)


# ── World Layer ──

func _build_world_layer() -> void:
	world_layer = Node2D.new()
	world_layer.name = "WorldLayer"
	add_child(world_layer)

	# Terrain tilemap
	terrain_map = TileMapController.new()
	terrain_map.name = "TerrainMap"
	world_layer.add_child(terrain_map)

	# Resource icons overlay
	resource_overlay = ResourceOverlay.new()
	resource_overlay.name = "ResourceOverlay"
	world_layer.add_child(resource_overlay)

	# Furniture icons overlay
	furniture_overlay = FurnitureOverlay.new()
	furniture_overlay.name = "FurnitureOverlay"
	world_layer.add_child(furniture_overlay)

	# Character sprites manager
	char_manager = CharacterManager.new()
	char_manager.name = "Characters"
	world_layer.add_child(char_manager)


# ── Camera & Visual Effects ──

func _build_camera_and_fx() -> void:
	# Camera
	game_camera = GameCamera.new()
	game_camera.name = "Camera2D"
	add_child(game_camera)

	# Weather particles (rain, lightning)
	weather_fx = WeatherFX.new()
	weather_fx.name = "WeatherFX"
	add_child(weather_fx)

	# Day/night color modulation
	day_night = DayNightCycle.new()
	day_night.name = "DayNightOverlay"
	add_child(day_night)


# ── UI Layer (CanvasLayer) ──

func _build_ui_layer() -> void:
	ui_layer = CanvasLayer.new()
	ui_layer.name = "UILayer"
	ui_layer.layer = 10
	add_child(ui_layer)

	# UIManager — central Control filling viewport, provides theme
	ui_manager = UIManager.new()
	ui_manager.name = "UIManager"
	ui_layer.add_child(ui_manager)

	# ── Top Bar ──
	var top_bar := HBoxContainer.new()
	top_bar.name = "TopBar"
	top_bar.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	top_bar.offset_bottom = 40
	ui_manager.add_child(top_bar)

	header = HeaderBar.new()
	header.name = "HeaderBar"
	header.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top_bar.add_child(header)

	# ── Side Panel (right, 300px, tabbed) ──
	side_panel = SidePanel.new()
	side_panel.name = "SidePanel"
	ui_manager.add_child(side_panel)

	status_panel = StatusPanel.new()
	npc_list = NPCListPanel.new()
	market_panel = MarketPanel.new()
	settings_panel = SettingsPanel.new()
	side_panel.setup_tabs(status_panel, npc_list, market_panel, settings_panel)

	# ── Narrative Panel (left side) ──
	narrative = NarrativePanel.new()
	narrative.name = "NarrativePanel"
	narrative.anchor_left = 0.0
	narrative.anchor_right = 0.0
	narrative.anchor_top = 0.0
	narrative.anchor_bottom = 1.0
	narrative.offset_left = 8
	narrative.offset_right = 320
	narrative.offset_top = 44
	narrative.offset_bottom = -88
	ui_manager.add_child(narrative)

	# ── God Panel (center top overlay) ──
	god_panel = GodPanel.new()
	god_panel.name = "GodPanel"
	god_panel.anchor_left = 0.3
	god_panel.anchor_right = 0.7
	god_panel.anchor_top = 0.0
	god_panel.anchor_bottom = 0.0
	god_panel.offset_top = 44
	god_panel.offset_bottom = 130
	ui_manager.add_child(god_panel)

	# ── Mini Map (top right corner, 160x160) ──
	mini_map = MiniMapPanel.new()
	mini_map.name = "MiniMapPanel"
	mini_map.anchor_left = 1.0
	mini_map.anchor_right = 1.0
	mini_map.anchor_top = 0.0
	mini_map.anchor_bottom = 0.0
	mini_map.offset_left = -480
	mini_map.offset_right = -310
	mini_map.offset_top = 44
	mini_map.offset_bottom = 210
	ui_manager.add_child(mini_map)

	# ── Action Bar (bottom center) ──
	action_bar = ActionBar.new()
	action_bar.name = "ActionBar"
	action_bar.anchor_left = 0.25
	action_bar.anchor_right = 0.75
	action_bar.anchor_top = 1.0
	action_bar.anchor_bottom = 1.0
	action_bar.offset_top = -180  # grow upward from bottom
	action_bar.offset_bottom = -40  # above talk bar
	action_bar.alignment = BoxContainer.ALIGNMENT_CENTER
	ui_manager.add_child(action_bar)

	# ── Dialogue Panel (center bottom, hidden) ──
	dialogue = DialoguePanel.new()
	dialogue.name = "DialoguePanel"
	dialogue.anchor_left = 0.2
	dialogue.anchor_right = 0.8
	dialogue.anchor_top = 1.0
	dialogue.anchor_bottom = 1.0
	dialogue.offset_top = -220
	dialogue.offset_bottom = -50
	ui_manager.add_child(dialogue)

	# ── Character Detail (modal overlay, hidden) ──
	char_detail = CharacterDetail.new()
	char_detail.name = "CharacterDetail"
	ui_manager.add_child(char_detail)

	# Register overlays with UIManager
	ui_manager.register_panel("side_panel", side_panel)
	ui_manager.register_panel("narrative", narrative)
	ui_manager.register_panel("god_panel", god_panel)
	ui_manager.register_panel("mini_map", mini_map)
	ui_manager.register_panel("dialogue", dialogue)
	ui_manager.register_panel("char_detail", char_detail)

	# ── Talk Bar (bottom, below action bar) ──
	var talk_bar := HBoxContainer.new()
	talk_bar.name = "TalkBar"
	talk_bar.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	talk_bar.offset_top = -44
	talk_bar.offset_bottom = 0
	# Place it at very bottom
	talk_bar.anchor_top = 1.0
	talk_bar.anchor_bottom = 1.0
	talk_bar.offset_top = -36
	talk_bar.offset_bottom = -4
	talk_bar.offset_left = 8
	talk_bar.offset_right = -8
	talk_bar.add_theme_constant_override("separation", 6)
	ui_layer.add_child(talk_bar)

	talk_input = LineEdit.new()
	talk_input.placeholder_text = "先在右侧选择 NPC..."
	talk_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	talk_input.text_submitted.connect(func(_t): _on_talk_send())
	talk_bar.add_child(talk_input)

	talk_send_btn = Button.new()
	talk_send_btn.text = "说话"
	talk_send_btn.pressed.connect(_on_talk_send)
	talk_bar.add_child(talk_send_btn)


# ════════════════════════════════════════════════════════
#  SIGNAL WIRING
# ════════════════════════════════════════════════════════

func _connect_signals() -> void:
	# ── WebSocket ──
	ws_client.message_received.connect(_on_ws_message)
	ws_client.connected.connect(func():
		header.set_connected(true)
		narrative.append_system("[color=#4ecca3]已连接到服务器[/color]"))
	ws_client.disconnected.connect(func():
		header.set_connected(false)
		narrative.append_system("[color=#e94560]连接断开，正在重连...[/color]"))

	# ── GameState ──
	GameState.world_state_updated.connect(_on_world_updated)
	GameState.dialogue_received.connect(func(d): dialogue.show_dialogue(d))
	GameState.dialogue_cleared.connect(func(): dialogue.hide_dialogue())
	GameState.event_received.connect(_on_event)
	GameState.settings_updated.connect(func(s): settings_panel.update_settings(s))
	GameState.token_updated.connect(func(t): header.update_token(t))
	GameState.season_changed.connect(func(s):
		header.update_season(s, GameState.season_name))

	# ── Header bar ──
	header.simulation_toggled.connect(_toggle_simulation)
	header.home_pressed.connect(_go_home)

	# ── Dialogue ──
	dialogue.reply_sent.connect(_on_dialogue_reply)

	# ── Status panel ──
	status_panel.action_requested.connect(_send_action)

	# ── NPC list ──
	npc_list.talk_requested.connect(_on_talk_to_npc)
	npc_list.trade_requested.connect(func(_id): pass)  # TODO: trade UI
	npc_list.detail_requested.connect(_on_character_detail_requested)

	# ── Market panel ──
	market_panel.action_requested.connect(_send_action)

	# ── Action bar ──
	action_bar.action_requested.connect(_send_action)

	# ── Settings panel ──
	settings_panel.control_requested.connect(func(msg): ws_client.send_json(msg))
	settings_panel.go_home.connect(_go_home)

	# ── Mini map ──
	mini_map.map_clicked.connect(func(wx: int, wy: int):
		game_camera.global_position = Vector2(wx * TILE_SIZE + TILE_SIZE / 2.0, wy * TILE_SIZE + TILE_SIZE / 2.0))

	# ── Character manager (world sprites) ──
	char_manager.character_selected.connect(_on_character_selected)
	char_manager.character_detail_requested.connect(_on_character_detail_requested)

	# ── Character detail overlay ──
	char_detail.close_requested.connect(func(): ui_manager.hide_overlay())
	char_detail.talk_requested.connect(func(npc_id):
		_on_talk_to_npc_by_id(npc_id))
	char_detail.trade_requested.connect(func(_id): pass)  # TODO: trade UI


# ════════════════════════════════════════════════════════
#  WORLD STATE UPDATE — called every server tick
# ════════════════════════════════════════════════════════

func _on_ws_message(data: Dictionary) -> void:
	if data.get("type") == "world_state":
		GameState.update_from_server(data)


func _on_world_updated() -> void:
	var tiles_data: Array = GameState.tiles
	var npcs_data: Array = GameState.npcs
	var player_data: Dictionary = GameState.player

	# ── World layer updates ──
	terrain_map.update_from_world_data(tiles_data)
	resource_overlay.update_from_world_data(tiles_data)
	furniture_overlay.update_from_world_data(tiles_data)
	char_manager.update_characters(npcs_data, player_data)

	# ── Camera follow ──
	if not player_data.is_empty():
		var px: int = player_data.get("x", 0)
		var py: int = player_data.get("y", 0)
		var target_pos := Vector2(px * TILE_SIZE + TILE_SIZE / 2.0, py * TILE_SIZE + TILE_SIZE / 2.0)
		# If character manager has a player node, follow it for smooth motion
		if char_manager.player_node != null:
			game_camera.set_follow_target(char_manager.player_node)
		else:
			game_camera.global_position = target_pos

	# ── Weather & day/night ──
	weather_fx.set_weather(GameState.weather)
	var time_data: Dictionary = GameState.time_data
	var phase: String = time_data.get("phase", "day")
	day_night.set_time_and_season(phase, GameState.season)

	# ── UI updates ──
	header.update_time(GameState.time_data, GameState.weather)
	header.update_simulation(GameState.simulation_running)
	header.update_token(GameState.token_usage)

	status_panel.update_status(player_data)
	npc_list.update_list(npcs_data, player_data)
	var at_exchange := GameState.is_player_at_exchange()
	market_panel.update_market(GameState.market, at_exchange)
	action_bar.update_context(at_exchange, player_data.get("is_god_mode", false))
	mini_map.update_map(player_data, tiles_data, npcs_data)
	god_panel.update_narrative(GameState.god_commentary, GameState.god_season, GameState.narrative_stage)

	# Refresh character detail if open
	if char_detail.visible:
		char_detail.refresh()


# ════════════════════════════════════════════════════════
#  EVENT HANDLING
# ════════════════════════════════════════════════════════

func _on_event(evt: Dictionary) -> void:
	narrative.append_event(evt)
	market_panel.add_trade_event(evt)


func _on_dialogue_reply(npc_id: String, msg: String) -> void:
	_send_action({"action": "dialogue_reply", "to_npc_id": npc_id, "message": msg})
	narrative.append_system("[color=#87ceeb]你回复: %s[/color]" % msg)


func _on_character_selected(character_id: String) -> void:
	# Set talk target to the selected character
	for npc in GameState.npcs:
		if npc is Dictionary and npc.get("npc_id", npc.get("id", "")) == character_id:
			var npc_name: String = npc.get("name", character_id)
			_talk_target_id = character_id
			_talk_target_name = npc_name
			talk_input.placeholder_text = "对 %s 说..." % npc_name
			return
	# Might be the player character -- ignore talk target change
	_talk_target_id = ""
	_talk_target_name = ""
	talk_input.placeholder_text = "先选择一个 NPC..."


func _on_character_detail_requested(character_id: String) -> void:
	# Find NPC data and show character detail overlay
	for npc in GameState.npcs:
		if npc is Dictionary and npc.get("npc_id", npc.get("id", "")) == character_id:
			char_detail.show_character(npc)
			ui_manager.show_overlay("char_detail")
			return


# ════════════════════════════════════════════════════════
#  TALK / ACTIONS / INPUT
# ════════════════════════════════════════════════════════

func _on_talk_to_npc(npc_id: String, npc_name: String) -> void:
	_talk_target_id = npc_id
	_talk_target_name = npc_name
	talk_input.placeholder_text = "对 %s 说..." % npc_name
	talk_input.grab_focus()


func _on_talk_to_npc_by_id(npc_id: String) -> void:
	# Resolve name from GameState
	for npc in GameState.npcs:
		if npc is Dictionary and npc.get("id", "") == npc_id:
			_on_talk_to_npc(npc_id, npc.get("name", npc_id))
			return
	_on_talk_to_npc(npc_id, npc_id)


func _on_talk_send() -> void:
	var msg := talk_input.text.strip_edges()
	if msg.is_empty() or _talk_target_id.is_empty():
		return
	_send_action({"action": "talk", "message": msg, "target_id": _talk_target_id})
	narrative.append_system("[color=#87ceeb]你说: %s[/color]" % msg)
	talk_input.text = ""


func _send_action(action: Dictionary) -> void:
	action["type"] = "player_action"
	ws_client.send_json(action)


func _toggle_simulation() -> void:
	var cmd: String = "stop_simulation" if GameState.simulation_running else "start_simulation"
	ws_client.send_json({"type": "control", "command": cmd})


func _go_home() -> void:
	ws_client.close_connection()
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")


# ════════════════════════════════════════════════════════
#  KEYBOARD INPUT
# ════════════════════════════════════════════════════════

func _unhandled_input(event: InputEvent) -> void:
	# Don't capture keys when typing in a text field
	if get_viewport().gui_get_focus_owner() is LineEdit:
		return
	if not (event is InputEventKey and event.pressed and not event.echo):
		return

	match event.keycode:
		# Movement — WASD / arrow keys
		KEY_W, KEY_UP:
			_send_action({"action": "move", "dx": 0, "dy": -1})
		KEY_S, KEY_DOWN:
			_send_action({"action": "move", "dx": 0, "dy": 1})
		KEY_A, KEY_LEFT:
			_send_action({"action": "move", "dx": -1, "dy": 0})
		KEY_D, KEY_RIGHT:
			_send_action({"action": "move", "dx": 1, "dy": 0})

		# Quick actions
		KEY_G:
			_send_action({"action": "gather"})
		KEY_E:
			_send_action({"action": "eat"})
		KEY_R:
			_send_action({"action": "rest"})
		KEY_Z:
			_send_action({"action": "sleep"})

		# Simulation toggle
		KEY_SPACE:
			_toggle_simulation()

		# Side panel toggle
		KEY_T:
			if side_panel.is_open():
				side_panel.close_panel()
			else:
				side_panel.open_panel()

		# Mini map toggle
		KEY_M:
			ui_manager.toggle_panel("mini_map")

		# Cycle side panel tabs
		KEY_TAB:
			if side_panel.is_open():
				var idx := side_panel.get_current_tab_index()
				var count := side_panel.tab_container.get_tab_count()
				side_panel.switch_to_tab((idx + 1) % count)

		# Camera recenter to player
		KEY_HOME:
			if char_manager.player_node != null:
				game_camera.global_position = char_manager.player_node.global_position
