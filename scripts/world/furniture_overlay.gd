class_name FurnitureOverlay
extends Node2D
## 家具图标覆盖层。在放置了家具的格子上显示对应图标。

# 家具类型 → 纹理路径映射
const FURNITURE_TEXTURES: Dictionary = {
	"bed":   "res://resources/art/icons/bed.png",    # 床
	"table": "res://resources/art/icons/table.png",  # 桌子
	"chair": "res://resources/art/icons/chair.png",  # 椅子
}

# 精灵节点池："x,y" → Sprite2D
var sprites: Dictionary = {}
# 纹理缓存：furniture_type → Texture2D
var texture_cache: Dictionary = {}


func _ready() -> void:
	_load_textures()


## 预加载所有家具纹理（仅加载存在的文件）
func _load_textures() -> void:
	for ftype: String in FURNITURE_TEXTURES:
		var path: String = FURNITURE_TEXTURES[ftype]
		if ResourceLoader.exists(path):
			texture_cache[ftype] = load(path)
		else:
			push_warning("FurnitureOverlay: 纹理不存在 '%s'（家具类型 '%s'）" % [path, ftype])


## 根据世界数据更新家具图标显示
## tiles: 包含格子信息的数组，每个元素为 Dictionary:
##   { "x": int, "y": int, "f": String|null, ... }
func update_from_world_data(tiles: Array) -> void:
	var active_keys: Dictionary = {}

	for tile: Variant in tiles:
		if not tile is Dictionary:
			continue

		var tile_dict: Dictionary = tile as Dictionary

		# 必须有家具字段且非空
		if not tile_dict.has("f") or tile_dict["f"] == null:
			continue

		var ftype: String = tile_dict["f"] as String
		if ftype.is_empty():
			continue

		var x: int = tile_dict.get("x", 0) as int
		var y: int = tile_dict.get("y", 0) as int
		var key: String = "%d,%d" % [x, y]
		active_keys[key] = true

		# 按需创建精灵节点
		if not sprites.has(key):
			var sprite := Sprite2D.new()
			add_child(sprite)
			sprites[key] = sprite

		var sprite: Sprite2D = sprites[key] as Sprite2D
		# 放置在格子中心偏下（家具视觉锚点略低于中心）
		sprite.position = Vector2(x * 32 + 16, y * 32 + 24)

		# 设置纹理
		if texture_cache.has(ftype):
			sprite.texture = texture_cache[ftype]

		sprite.visible = true

	# 隐藏不再有家具的格子精灵
	for key: String in sprites:
		if not active_keys.has(key):
			(sprites[key] as Sprite2D).visible = false


## 清除所有精灵节点（场景切换时调用）
func clear_all() -> void:
	for key: String in sprites:
		var sprite: Sprite2D = sprites[key] as Sprite2D
		sprite.queue_free()
	sprites.clear()
