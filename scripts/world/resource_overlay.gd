class_name ResourceOverlay
extends Node2D
## 资源图标覆盖层。在含有可采集资源的格子上显示对应图标，透明度随剩余数量变化。

# 资源类型代码 → 纹理路径映射
const RESOURCE_TEXTURES: Dictionary = {
	"w": "res://resources/art/icons/res_wood.png",   # 木材
	"s": "res://resources/art/icons/res_stone.png",  # 石材
	"o": "res://resources/art/icons/res_ore.png",    # 矿石
	"f": "res://resources/art/icons/res_food.png",   # 食物
	"h": "res://resources/art/icons/res_herb.png",   # 草药
}

# 精灵节点池："x,y" → Sprite2D
var sprites: Dictionary = {}
# 纹理缓存：type_code → Texture2D
var texture_cache: Dictionary = {}


func _ready() -> void:
	_load_textures()


## 预加载所有资源纹理（仅加载存在的文件）
func _load_textures() -> void:
	for code: String in RESOURCE_TEXTURES:
		var path: String = RESOURCE_TEXTURES[code]
		if ResourceLoader.exists(path):
			texture_cache[code] = load(path)
		else:
			push_warning("ResourceOverlay: 纹理不存在 '%s'（资源代码 '%s'）" % [path, code])


## 根据世界数据更新资源图标显示
## tiles: 包含格子信息的数组，每个元素为 Dictionary:
##   { "x": int, "y": int, "r": String, "q": int, "mq": int, ... }
func update_from_world_data(tiles: Array) -> void:
	var active_keys: Dictionary = {}

	for tile: Variant in tiles:
		if not tile is Dictionary:
			continue

		var tile_dict: Dictionary = tile as Dictionary

		# 必须有资源类型和数量
		if not tile_dict.has("r") or not tile_dict.has("q"):
			continue

		var q: int = tile_dict["q"] as int
		if q <= 0:
			continue

		var x: int = tile_dict.get("x", 0) as int
		var y: int = tile_dict.get("y", 0) as int
		var key: String = "%d,%d" % [x, y]
		var res_type: String = tile_dict["r"] as String
		active_keys[key] = true

		# 按需创建精灵节点
		if not sprites.has(key):
			var sprite := Sprite2D.new()
			add_child(sprite)
			sprites[key] = sprite

		var sprite: Sprite2D = sprites[key] as Sprite2D
		# 放置在格子中心 (每格 32px)
		sprite.position = Vector2(x * 32 + 16, y * 32 + 16)

		# 设置纹理
		if texture_cache.has(res_type):
			sprite.texture = texture_cache[res_type]

		# 根据剩余数量 / 最大数量调整透明度
		# 数量越少越透明，最低 0.3，最高 1.0
		var mq: int = tile_dict.get("mq", 10) as int
		if mq <= 0:
			mq = 10
		var ratio: float = float(q) / float(mq)
		sprite.modulate.a = clampf(ratio * 0.8 + 0.2, 0.3, 1.0)
		sprite.visible = true

	# 隐藏不再有资源的格子精灵
	for key: String in sprites:
		if not active_keys.has(key):
			(sprites[key] as Sprite2D).visible = false


## 清除所有精灵节点（场景切换时调用）
func clear_all() -> void:
	for key: String in sprites:
		var sprite: Sprite2D = sprites[key] as Sprite2D
		sprite.queue_free()
	sprites.clear()
