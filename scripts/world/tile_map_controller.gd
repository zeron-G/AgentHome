class_name TileMapController
extends TileMapLayer
## 地图控制器：从 PNG 纹理程序化创建 TileSet，根据后端数据刷新格子。
##
## 20x20 网格，每格 32x32 像素 = 640x640 像素世界。
## 后端地块类型: "g"=草地, "f"=森林, "r"=岩石, "w"=水域, "o"=城镇, exchange("e":1)

# ── 常量 ──

const GRID_SIZE: int = 20
const TILE_PX: int = 32

## 地块类型 → 纹理文件名列表（变体）
const TILE_VARIANTS: Dictionary = {
	"g": ["grass_0", "grass_1", "grass_2", "grass_3"],
	"f": ["forest_0", "forest_1", "forest_2"],
	"r": ["rock_0", "rock_1"],
	"w": ["water_0"],
	"o": ["town_0", "town_1"],
}

const EXCHANGE_TEXTURE_NAME: String = "exchange"
const TILESET_DIR: String = "res://resources/art/tileset/"

# ── 内部状态 ──

## 纹理名 → {source_id: int, atlas_coords: Vector2i}
var _tile_lookup: Dictionary = {}

## 地块类型 → [{source_id, atlas_coords}] （用于变体随机选取）
var _type_to_entries: Dictionary = {}

## exchange 专用条目
var _exchange_entry: Dictionary = {}

## 回退纯色纹理（当 PNG 缺失时使用）
var _fallback_colors: Dictionary = {
	"g": Color(0.38, 0.65, 0.28),   # 草地绿
	"f": Color(0.18, 0.42, 0.16),   # 森林深绿
	"r": Color(0.55, 0.54, 0.52),   # 岩石灰
	"w": Color(0.22, 0.46, 0.72),   # 水域蓝
	"o": Color(0.68, 0.55, 0.34),   # 城镇棕
	"exchange": Color(0.85, 0.65, 0.13),  # 交易所金
}

## 当前已缓存的 tile 数据的哈希，用于跳过无变化的刷新
var _last_tiles_hash: int = 0


func _ready() -> void:
	_build_tileset()


# ════════════════════════════════════════════════════════════
#  TileSet 构建
# ════════════════════════════════════════════════════════════

func _build_tileset() -> void:
	var ts := TileSet.new()
	ts.tile_size = Vector2i(TILE_PX, TILE_PX)

	var source_index: int = 0

	# 为每种地块类型的每个变体创建一个 TileSetAtlasSource
	for tile_type: String in TILE_VARIANTS:
		var variants: Array = TILE_VARIANTS[tile_type]
		var entries: Array = []
		for variant_name: String in variants:
			var entry := _create_atlas_source(ts, variant_name, tile_type, source_index)
			if not entry.is_empty():
				entries.append(entry)
				_tile_lookup[variant_name] = entry
				source_index += 1
		if entries.size() > 0:
			_type_to_entries[tile_type] = entries
		else:
			# 所有变体都缺失 — 创建纯色回退
			var fb_entry := _create_fallback_source(ts, tile_type, source_index)
			_type_to_entries[tile_type] = [fb_entry]
			source_index += 1

	# Exchange 纹理
	var ex_entry := _create_atlas_source(ts, EXCHANGE_TEXTURE_NAME, "exchange", source_index)
	if not ex_entry.is_empty():
		_exchange_entry = ex_entry
		source_index += 1
	else:
		_exchange_entry = _create_fallback_source(ts, "exchange", source_index)
		source_index += 1

	tile_set = ts


## 从 PNG 文件创建单格 Atlas 源。成功返回 {source_id, atlas_coords}，失败返回 {}。
func _create_atlas_source(ts: TileSet, texture_name: String, tile_type: String, idx: int) -> Dictionary:
	var path := TILESET_DIR + texture_name + ".png"
	if not ResourceLoader.exists(path):
		push_warning("TileMapController: 纹理缺失 — %s" % path)
		return {}

	var tex: Texture2D = load(path)
	if tex == null:
		push_warning("TileMapController: 无法加载纹理 — %s" % path)
		return {}

	var source := TileSetAtlasSource.new()
	source.texture = tex
	source.texture_region_size = Vector2i(TILE_PX, TILE_PX)

	# 创建单个 tile 于 atlas 坐标 (0, 0)
	source.create_tile(Vector2i.ZERO)

	var source_id: int = ts.add_source(source, idx)
	return {"source_id": source_id, "atlas_coords": Vector2i.ZERO}


## 当 PNG 缺失时，用纯色 Image 生成回退纹理。
func _create_fallback_source(ts: TileSet, tile_type: String, idx: int) -> Dictionary:
	var color: Color = _fallback_colors.get(tile_type, Color.MAGENTA)
	var img := Image.create(TILE_PX, TILE_PX, false, Image.FORMAT_RGBA8)
	img.fill(color)
	var tex := ImageTexture.create_from_image(img)

	var source := TileSetAtlasSource.new()
	source.texture = tex
	source.texture_region_size = Vector2i(TILE_PX, TILE_PX)
	source.create_tile(Vector2i.ZERO)

	var source_id: int = ts.add_source(source, idx)
	push_warning("TileMapController: 使用回退颜色 %s 作为地块类型 '%s'" % [color, tile_type])
	return {"source_id": source_id, "atlas_coords": Vector2i.ZERO}


# ════════════════════════════════════════════════════════════
#  世界数据刷新
# ════════════════════════════════════════════════════════════

## 从后端 tiles 数组更新整个地图。
## tiles: Array of Dictionary，每项 {"x": int, "y": int, "t": str, "e": 0|1, "r": str, "q": int, ...}
func update_from_world_data(tiles: Array) -> void:
	if tiles.is_empty():
		return

	# 简单哈希检测：如果数据没变就跳过
	var new_hash := tiles.hash()
	if new_hash == _last_tiles_hash:
		return
	_last_tiles_hash = new_hash

	for tile_data: Variant in tiles:
		if not tile_data is Dictionary:
			continue
		var td: Dictionary = tile_data
		var gx: int = td.get("x", 0)
		var gy: int = td.get("y", 0)
		var tile_type: String = td.get("t", "g")
		var is_exchange: bool = (td.get("e", 0) == 1)

		var cell_coords := Vector2i(gx, gy)

		if is_exchange and not _exchange_entry.is_empty():
			set_cell(cell_coords, _exchange_entry["source_id"], _exchange_entry["atlas_coords"])
		else:
			var entry := _pick_variant(tile_type, gx, gy)
			if not entry.is_empty():
				set_cell(cell_coords, entry["source_id"], entry["atlas_coords"])


## 根据坐标哈希确定性地选取一个变体。
func _pick_variant(tile_type: String, gx: int, gy: int) -> Dictionary:
	var entries: Array = _type_to_entries.get(tile_type, [])
	if entries.is_empty():
		# 未知类型 — 尝试草地作为兜底
		entries = _type_to_entries.get("g", [])
		if entries.is_empty():
			return {}
	var variant_hash: int = absi(gx * 31 + gy * 17)
	var index: int = variant_hash % entries.size()
	return entries[index]


# ════════════════════════════════════════════════════════════
#  坐标转换工具
# ════════════════════════════════════════════════════════════

## 网格坐标 → 像素世界坐标（格子中心）
func get_world_position(grid_x: int, grid_y: int) -> Vector2:
	return Vector2(grid_x * TILE_PX + TILE_PX / 2.0, grid_y * TILE_PX + TILE_PX / 2.0)


## 像素世界坐标 → 网格坐标
func get_grid_position(world_pos: Vector2) -> Vector2i:
	return Vector2i(int(world_pos.x / TILE_PX), int(world_pos.y / TILE_PX))


## 网格坐标是否在 20x20 有效范围内
func is_valid_grid_pos(gx: int, gy: int) -> bool:
	return gx >= 0 and gx < GRID_SIZE and gy >= 0 and gy < GRID_SIZE
