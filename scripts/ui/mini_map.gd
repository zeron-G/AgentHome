class_name MiniMapPanel
extends VBoxContainer
## Visual mini-map using Canvas _draw(). Renders colored tile rectangles,
## NPC dots, player diamond, resource markers, exchange borders, and a
## viewport rectangle. Click to emit map_clicked for camera jump.
## Inherits dark tarot theme from UIManager.

signal map_clicked(world_x: int, world_y: int)

# ── Constants ──
const MAP_RADIUS := 5          # tiles in each direction from player
const MAP_GRID := 11           # MAP_RADIUS * 2 + 1
const MIN_MAP_SIZE := 160.0    # minimum pixel size for map canvas

# Tile type → fill color
const TILE_COLORS := {
	"g": Color("#2a4a2a"),   # grass
	"f": Color("#1a3a1a"),   # forest
	"r": Color("#5a5a5a"),   # rock
	"w": Color("#1a3a5a"),   # water
	"o": Color("#5a4a3a"),   # town
}
const COLOR_EXCHANGE_BORDER := Color("#c8a832")
const COLOR_RESOURCE := Color("#f5a623")
const COLOR_PLAYER := Color("#e94560")
const COLOR_NPC_DEFAULT := Color("#4ecca3")
const COLOR_VIEWPORT_RECT := Color(1, 1, 1, 0.2)
const COLOR_GRID_LINE := Color(1, 1, 1, 0.05)
const COLOR_BG := Color("#0a0a14")

# ── State ──
var _player_data: Dictionary = {}
var _tile_data: Array = []
var _npc_data: Array = []

# Nodes
var _title_label: Label
var _map_canvas: Control
var _legend: RichTextLabel


func _ready() -> void:
	add_theme_constant_override("separation", 4)

	# Title
	_title_label = Label.new()
	_title_label.text = "小地图"
	_title_label.add_theme_font_size_override("font_size", 14)
	_title_label.add_theme_color_override("font_color", Color("#c8a832"))
	add_child(_title_label)

	# Map canvas (custom draw Control)
	_map_canvas = _MapCanvas.new()
	_map_canvas.custom_minimum_size = Vector2(MIN_MAP_SIZE, MIN_MAP_SIZE)
	_map_canvas.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_map_canvas.size_flags_vertical = Control.SIZE_EXPAND_FILL
	(_map_canvas as _MapCanvas).parent_panel = self
	_map_canvas.gui_input.connect(_on_map_input)
	add_child(_map_canvas)

	# Legend
	_legend = RichTextLabel.new()
	_legend.bbcode_enabled = true
	_legend.fit_content = true
	_legend.custom_minimum_size.y = 32
	_legend.add_theme_font_size_override("normal_font_size", 11)
	_legend.append_text(
		"[color=#e94560]◆[/color]=你  " +
		"[color=#4ecca3]●[/color]=NPC  " +
		"[color=#f5a623]◦[/color]=资源  " +
		"[color=#c8a832]□[/color]=交易所"
	)
	add_child(_legend)


# ── Public API (kept compatible) ──

func update_map(player: Dictionary, tiles: Array, npcs: Array) -> void:
	_player_data = player
	_tile_data = tiles
	_npc_data = npcs
	_map_canvas.queue_redraw()


# ── Input → signal ──

func _on_map_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		if _player_data.is_empty():
			return
		var px: int = _player_data.get("x", 0)
		var py: int = _player_data.get("y", 0)
		var canvas_size: Vector2 = _map_canvas.size
		var cell: float = _cell_size(canvas_size)
		var ox: float = (canvas_size.x - cell * MAP_GRID) * 0.5
		var oy: float = (canvas_size.y - cell * MAP_GRID) * 0.5
		var local: Vector2 = event.position
		var gx: int = int(floor((local.x - ox) / cell)) - MAP_RADIUS
		var gy: int = int(floor((local.y - oy) / cell)) - MAP_RADIUS
		var world_x: int = px + gx
		var world_y: int = py + gy
		map_clicked.emit(world_x, world_y)


# ── Helpers used by inner class ──

func _cell_size(canvas_size: Vector2) -> float:
	var available := minf(canvas_size.x, canvas_size.y)
	return available / float(MAP_GRID)


func get_tile_lookup() -> Dictionary:
	var lookup: Dictionary = {}
	for tile in _tile_data:
		if tile is Dictionary:
			lookup["%d,%d" % [tile.get("x", 0), tile.get("y", 0)]] = tile
	return lookup


func get_npc_lookup() -> Dictionary:
	# key → {color: Color, name: String}
	var lookup: Dictionary = {}
	for npc in _npc_data:
		if npc is Dictionary:
			var key: String = "%d,%d" % [npc.get("x", 0), npc.get("y", 0)]
			var c: String = npc.get("color", "#4ecca3")
			lookup[key] = Color.from_string(c, COLOR_NPC_DEFAULT)
	return lookup


# ══════════════════════════════════════════════════════════════
# Inner Control that handles _draw() — keeps MiniMapPanel as VBoxContainer.
# ══════════════════════════════════════════════════════════════

class _MapCanvas extends Control:
	var parent_panel: MiniMapPanel

	func _draw() -> void:
		if parent_panel == null:
			return
		if parent_panel._player_data.is_empty():
			_draw_empty()
			return

		var px: int = parent_panel._player_data.get("x", 0)
		var py: int = parent_panel._player_data.get("y", 0)
		var canvas_size: Vector2 = size
		var cell: float = parent_panel._cell_size(canvas_size)
		var ox: float = (canvas_size.x - cell * MAP_GRID) * 0.5
		var oy: float = (canvas_size.y - cell * MAP_GRID) * 0.5
		var tile_lookup: Dictionary = parent_panel.get_tile_lookup()
		var npc_lookup: Dictionary = parent_panel.get_npc_lookup()

		# Background
		draw_rect(Rect2(Vector2.ZERO, canvas_size), COLOR_BG)

		# Draw tiles
		for dy in range(-MAP_RADIUS, MAP_RADIUS + 1):
			for dx in range(-MAP_RADIUS, MAP_RADIUS + 1):
				var key: String = "%d,%d" % [px + dx, py + dy]
				var cx: float = ox + float(dx + MAP_RADIUS) * cell
				var cy: float = oy + float(dy + MAP_RADIUS) * cell
				var rect := Rect2(cx, cy, cell, cell)

				# Tile fill
				var fill_color: Color = TILE_COLORS.get("g", Color("#2a4a2a"))
				if tile_lookup.has(key):
					var tile: Dictionary = tile_lookup[key]
					var t: String = tile.get("t", "g")
					fill_color = TILE_COLORS.get(t, fill_color)
				draw_rect(rect, fill_color)

				# Exchange border
				if tile_lookup.has(key):
					var tile: Dictionary = tile_lookup[key]
					if tile.get("e", 0) == 1:
						draw_rect(rect, COLOR_EXCHANGE_BORDER, false, 2.0)

				# Resource marker (small dot)
				if tile_lookup.has(key):
					var tile: Dictionary = tile_lookup[key]
					if tile.has("r") and tile.get("q", 0) > 0:
						var dot_radius: float = maxf(cell * 0.15, 2.0)
						draw_circle(
							Vector2(cx + cell * 0.8, cy + cell * 0.2),
							dot_radius,
							COLOR_RESOURCE
						)

				# Grid lines (subtle)
				draw_rect(rect, COLOR_GRID_LINE, false, 1.0)

		# Draw NPC dots
		for dy in range(-MAP_RADIUS, MAP_RADIUS + 1):
			for dx in range(-MAP_RADIUS, MAP_RADIUS + 1):
				var key: String = "%d,%d" % [px + dx, py + dy]
				if npc_lookup.has(key):
					var npc_color: Color = npc_lookup[key]
					var cx: float = ox + float(dx + MAP_RADIUS) * cell + cell * 0.5
					var cy: float = oy + float(dy + MAP_RADIUS) * cell + cell * 0.5
					var dot_r: float = maxf(cell * 0.25, 3.0)
					draw_circle(Vector2(cx, cy), dot_r, npc_color)

		# Draw player as red diamond (center)
		var pcx: float = ox + float(MAP_RADIUS) * cell + cell * 0.5
		var pcy: float = oy + float(MAP_RADIUS) * cell + cell * 0.5
		var d: float = maxf(cell * 0.35, 4.0)
		var diamond := PackedVector2Array([
			Vector2(pcx, pcy - d),      # top
			Vector2(pcx + d, pcy),      # right
			Vector2(pcx, pcy + d),      # bottom
			Vector2(pcx - d, pcy),      # left
		])
		draw_colored_polygon(diamond, COLOR_PLAYER)

		# Viewport rectangle (shows approximate camera view area — 3x3 center)
		var vp_size: float = cell * 3.0
		var vp_x: float = ox + float(MAP_RADIUS - 1) * cell
		var vp_y: float = oy + float(MAP_RADIUS - 1) * cell
		draw_rect(Rect2(vp_x, vp_y, vp_size, vp_size), COLOR_VIEWPORT_RECT, false, 1.5)


	func _draw_empty() -> void:
		draw_rect(Rect2(Vector2.ZERO, size), COLOR_BG)
		# "无数据" centered
		var font := ThemeDB.fallback_font
		if font:
			var text := "无数据"
			var fsize := 14
			var text_size: Vector2 = font.get_string_size(text, HORIZONTAL_ALIGNMENT_CENTER, -1, fsize)
			var pos := Vector2(
				(size.x - text_size.x) * 0.5,
				(size.y + text_size.y) * 0.5
			)
			draw_string(font, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1, fsize, Color("#8888a0"))
