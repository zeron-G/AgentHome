class_name ZoneMap
extends RefCounted
## Maps tile coordinates to Chinese zone names and descriptions.


func get_zone_name(x: int, y: int) -> String:
	# Exchange center
	if x == 10 and y == 10:
		return "交易所"
	# Town area
	if x >= 9 and x <= 11 and y >= 9 and y <= 11:
		return "村中心"

	# Check tile type from cached world data
	var tile_type := _get_tile_type(x, y)
	match tile_type:
		"f":
			return "森林"
		"r":
			return "矿区"

	# Quadrant-based fallback for grass
	if x < 10 and y < 10:
		return "西北草地"
	if x >= 10 and y < 10:
		return "东北草地"
	if x < 10 and y >= 10:
		return "西南草地"
	return "东南草地"


func get_zone_description(x: int, y: int) -> String:
	var parts: PackedStringArray = []
	var tile_type := _get_tile_type(x, y)

	match tile_type:
		"g":
			parts.append("你站在一片开阔的草地上。")
		"f":
			parts.append("你身处茂密的森林中，周围是高大的树木。")
		"r":
			parts.append("你站在嶙峋的岩石区域，灰色的碎石遍地。")
		"o":
			parts.append("你在村子的中心区域，几间低矮的房屋围在四周。")
		_:
			parts.append("你站在一片未知的区域。")

	# Check resources
	var tile := _find_tile(x, y)
	if not tile.is_empty():
		var res_type = tile.get("r", "")
		var res_qty = tile.get("q", 0)
		if not res_type.is_empty() and res_qty > 0:
			var rname := _resource_name(res_type)
			parts.append("这里有%s（剩余 %d）。" % [rname, res_qty])

		if tile.get("e", 0) == 1:
			parts.append("交易所就在这里。")

		var furniture = tile.get("f", "")
		if not furniture.is_empty() and furniture is String:
			var fname := _furniture_name(furniture)
			parts.append("这里有一张%s。" % fname)

	return " ".join(parts)


func _get_tile_type(x: int, y: int) -> String:
	var tile := _find_tile(x, y)
	return tile.get("t", "g") if not tile.is_empty() else "g"


func _find_tile(x: int, y: int) -> Dictionary:
	for tile in GameState.tiles:
		if tile is Dictionary and tile.get("x", -1) == x and tile.get("y", -1) == y:
			return tile
	return {}


static func _resource_name(res_code: String) -> String:
	match res_code:
		"w": return "木头"
		"s": return "石头"
		"o": return "矿石"
		"f": return "食物"
		"h": return "草药"
		_:  return "资源"


static func _furniture_name(f: String) -> String:
	match f:
		"bed":   return "床"
		"table": return "桌子"
		"chair": return "椅子"
		_:       return "家具"
