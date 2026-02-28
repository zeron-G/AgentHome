class_name CharacterManager
extends Node2D
## 角色生命周期管理器：根据服务器数据创建、更新、删除 CharacterNode。

# ── 常量 ──

## 角色 ID → 精灵表路径
const SPRITE_PATHS: Dictionary = {
	"npc_he":       "res://resources/art/characters/npc_he.png",
	"npc_sui":      "res://resources/art/characters/npc_sui.png",
	"npc_shan":     "res://resources/art/characters/npc_shan.png",
	"npc_tang":     "res://resources/art/characters/npc_tang.png",
	"npc_kuang":    "res://resources/art/characters/npc_kuang.png",
	"npc_mu":       "res://resources/art/characters/npc_mu.png",
	"npc_lan":      "res://resources/art/characters/npc_lan.png",
	"npc_shi":      "res://resources/art/characters/npc_shi.png",
	"npc_shangren": "res://resources/art/characters/npc_shangren.png",
	"player":       "res://resources/art/characters/player.png",
}

## NPC 默认颜色（当后端未提供时）
const DEFAULT_NPC_COLOR: String = "#4ecca3"
const DEFAULT_PLAYER_COLOR: String = "#87ceeb"

# ── 状态 ──

## character_id → CharacterNode
var characters: Dictionary = {}

## 玩家节点的快速引用
var player_node: CharacterNode = null

## 当前选中的角色 ID
var _selected_id: String = ""

# ── 信号 ──

## 角色被单击选中
signal character_selected(character_id: String)

## 角色被双击（请求详情面板）
signal character_detail_requested(character_id: String)


# ════════════════════════════════════════════════════════════
#  批量更新入口
# ════════════════════════════════════════════════════════════

## 根据后端推送的数据更新所有角色。
## npcs: Array of Dictionary — NPC 列表
## player_data: Dictionary — 玩家数据（可以为空 {}）
func update_characters(npcs: Array, player_data: Dictionary) -> void:
	var seen_ids: Dictionary = {}

	# ── 更新/创建 NPC ──
	for npc_data: Variant in npcs:
		if not npc_data is Dictionary:
			continue
		var nd: Dictionary = npc_data
		var npc_id: String = nd.get("id", nd.get("npc_id", ""))
		if npc_id.is_empty():
			continue

		seen_ids[npc_id] = true

		if characters.has(npc_id):
			# 已存在 — 更新数据
			var node: CharacterNode = characters[npc_id]
			node.update_from_data(nd)
		else:
			# 新角色 — 创建
			var node := _create_character_node(npc_id, nd, false)
			if node:
				characters[npc_id] = node

	# ── 更新/创建玩家 ──
	if not player_data.is_empty():
		var pid: String = player_data.get("id", player_data.get("player_id", "player"))
		seen_ids[pid] = true

		if characters.has(pid):
			var node: CharacterNode = characters[pid]
			node.update_from_data(player_data)
		else:
			var node := _create_character_node(pid, player_data, true)
			if node:
				characters[pid] = node
				player_node = node

	# ── 移除不再存在的角色 ──
	var to_remove: Array[String] = []
	for cid: String in characters:
		if not seen_ids.has(cid):
			to_remove.append(cid)

	for cid: String in to_remove:
		_remove_character(cid)


# ════════════════════════════════════════════════════════════
#  角色节点创建与删除
# ════════════════════════════════════════════════════════════

## 创建一个新的 CharacterNode 并添加为子节点。
func _create_character_node(id: String, data: Dictionary, is_player_char: bool) -> CharacterNode:
	var node := CharacterNode.new()
	node.name = "Char_" + id

	# 确定精灵路径
	var sprite_path: String = _resolve_sprite_path(id)

	# 确定名称和颜色
	var char_name: String = data.get("name", id)
	var char_color: String
	if is_player_char:
		char_color = data.get("color", DEFAULT_PLAYER_COLOR)
	else:
		char_color = data.get("color", DEFAULT_NPC_COLOR)

	# 添加为子节点（先添加再 setup，这样 _ready 已经执行）
	add_child(node)

	# 初始化
	node.setup(id, char_name, char_color, sprite_path, is_player_char)

	# 设置初始位置
	var start_x: int = data.get("x", 0)
	var start_y: int = data.get("y", 0)
	node.teleport_to(start_x, start_y)

	# 从数据更新其余状态
	node.update_from_data(data)

	# 连接信号
	node.character_clicked.connect(_on_character_clicked)
	node.character_double_clicked.connect(_on_character_double_clicked)

	return node


## 根据角色 ID 查找精灵表路径。
func _resolve_sprite_path(id: String) -> String:
	# 直接匹配
	if SPRITE_PATHS.has(id):
		return SPRITE_PATHS[id]

	# 尝试去掉数字后缀匹配（如 "npc_he_2" → "npc_he"）
	var base_id := id
	while base_id.length() > 0 and base_id[-1].is_valid_int():
		base_id = base_id.substr(0, base_id.length() - 1)
	base_id = base_id.rstrip("_")
	if SPRITE_PATHS.has(base_id):
		return SPRITE_PATHS[base_id]

	# 默认回退 — 使用 player 精灵
	push_warning("CharacterManager: 未找到角色 '%s' 的精灵路径，使用默认" % id)
	return SPRITE_PATHS.get("player", "res://resources/art/characters/player.png")


## 移除一个角色节点。
func _remove_character(id: String) -> void:
	if not characters.has(id):
		return

	var node: CharacterNode = characters[id]

	# 断开信号
	if node.character_clicked.is_connected(_on_character_clicked):
		node.character_clicked.disconnect(_on_character_clicked)
	if node.character_double_clicked.is_connected(_on_character_double_clicked):
		node.character_double_clicked.disconnect(_on_character_double_clicked)

	# 清理选中状态
	if _selected_id == id:
		_selected_id = ""

	# 清理玩家引用
	if player_node == node:
		player_node = null

	node.queue_free()
	characters.erase(id)


# ════════════════════════════════════════════════════════════
#  查询接口
# ════════════════════════════════════════════════════════════

## 根据 ID 获取角色节点，不存在返回 null。
func get_character(id: String) -> CharacterNode:
	return characters.get(id)


## 获取玩家节点。
func get_player_node() -> CharacterNode:
	return player_node


## 获取当前选中的角色 ID（空字符串 = 无选中）。
func get_selected_id() -> String:
	return _selected_id


## 程序化选中指定角色。
func select_character(id: String) -> void:
	# 取消之前的选中
	if not _selected_id.is_empty() and characters.has(_selected_id):
		var prev: CharacterNode = characters[_selected_id]
		prev.is_selected = false

	_selected_id = id

	if not id.is_empty() and characters.has(id):
		var node: CharacterNode = characters[id]
		node.is_selected = true


## 取消所有选中状态。
func deselect_all() -> void:
	if not _selected_id.is_empty() and characters.has(_selected_id):
		var prev: CharacterNode = characters[_selected_id]
		prev.is_selected = false
	_selected_id = ""


## 获取所有 NPC 节点（不含玩家）。
func get_all_npc_nodes() -> Array[CharacterNode]:
	var result: Array[CharacterNode] = []
	for cid: String in characters:
		var node: CharacterNode = characters[cid]
		if not node.is_player:
			result.append(node)
	return result


## 获取角色总数。
func get_character_count() -> int:
	return characters.size()


# ════════════════════════════════════════════════════════════
#  信号处理
# ════════════════════════════════════════════════════════════

func _on_character_clicked(id: String) -> void:
	select_character(id)
	character_selected.emit(id)


func _on_character_double_clicked(id: String) -> void:
	select_character(id)
	character_detail_requested.emit(id)
