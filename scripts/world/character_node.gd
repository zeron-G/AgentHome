class_name CharacterNode
extends Node2D
## 地图上的单个角色节点（NPC 或玩家）。
##
## 子节点:
##   Body        — AnimatedSprite2D（精灵表动画）
##   NameLabel   — Label（角色名，显示在下方）
##   MoodIndicator — Sprite2D（16x16 心情图标，显示在上方）
##
## 精灵表格式: 128x96，4列x3行，每帧 32x32
##   列: down(0), left(1), right(2), up(3)
##   行: idle(0), walk_a(1), walk_b(2)

# ── 常量 ──

const TILE_PX: int = 32
const SPRITE_COLS: int = 4
const SPRITE_ROWS: int = 3
const FRAME_SIZE: Vector2i = Vector2i(32, 32)

## 方向列索引
const DIR_DOWN: int = 0
const DIR_LEFT: int = 1
const DIR_RIGHT: int = 2
const DIR_UP: int = 3

## 方向名称 → 列索引
const DIRECTION_MAP: Dictionary = {
	"down": DIR_DOWN,
	"left": DIR_LEFT,
	"right": DIR_RIGHT,
	"up": DIR_UP,
}

## 心情关键词 → 图标文件名
const MOOD_ICONS: Dictionary = {
	"happy":   "mood_happy",
	"sad":     "mood_sad",
	"angry":   "mood_angry",
	"neutral": "mood_neutral",
	"tired":   "mood_tired",
	"excited": "mood_excited",
}

const MOOD_ICON_DIR: String = "res://resources/art/ui/"

## 选中时高亮颜色
const SELECTION_COLOR := Color(1.0, 0.84, 0.0, 0.45)
const SELECTION_RADIUS: float = 18.0

## 处理中指示器闪烁
const PROCESSING_BLINK_SPEED: float = 3.0

# ── 导出/状态变量 ──

var character_id: String = ""
var character_name: String = ""
var character_color: Color = Color.WHITE
var grid_pos: Vector2i = Vector2i.ZERO
var target_pos: Vector2 = Vector2.ZERO
var move_speed: float = 128.0  # 像素/秒，平滑插值速度
var is_selected: bool = false:
	set(value):
		is_selected = value
		queue_redraw()
var is_player: bool = false
var is_processing: bool = false

var _current_direction: String = "down"
var _is_moving: bool = false
var _mood_text: String = ""
var _blink_timer: float = 0.0

# ── 子节点引用 ──

var _body: AnimatedSprite2D = null
var _name_label: Label = null
var _mood_indicator: Sprite2D = null
var _sprite_sheet: Texture2D = null

# ── 信号 ──

signal character_clicked(character_id: String)
signal character_double_clicked(character_id: String)


# ════════════════════════════════════════════════════════════
#  初始化
# ════════════════════════════════════════════════════════════

func _ready() -> void:
	# Body — AnimatedSprite2D（精灵动画）
	_body = AnimatedSprite2D.new()
	_body.name = "Body"
	add_child(_body)

	# NameLabel — 角色名标签，位于脚下
	_name_label = Label.new()
	_name_label.name = "NameLabel"
	_name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_name_label.position = Vector2(-40, 14)
	_name_label.size = Vector2(80, 20)
	_name_label.add_theme_font_size_override("font_size", 9)
	add_child(_name_label)

	# MoodIndicator — 心情图标，位于头顶
	_mood_indicator = Sprite2D.new()
	_mood_indicator.name = "MoodIndicator"
	_mood_indicator.position = Vector2(0, -20)
	_mood_indicator.visible = false
	add_child(_mood_indicator)


## 初始化角色：加载精灵、创建动画、设置名字标签。
## sprite_path: 例如 "res://resources/art/characters/npc_he.png"
func setup(id: String, char_name: String, color: String, sprite_path: String, is_player_char: bool = false) -> void:
	character_id = id
	character_name = char_name
	is_player = is_player_char

	# 解析颜色
	character_color = Color.from_string(color, Color.WHITE)

	# 名字标签
	if _name_label:
		_name_label.text = char_name
		_name_label.add_theme_color_override("font_color", character_color)

	# 加载精灵表
	_load_sprite_sheet(sprite_path)

	# 玩家角色稍微提高 z 轴优先级
	if is_player:
		z_index = 1000


## 从精灵表 PNG 加载并构建 SpriteFrames 动画资源。
func _load_sprite_sheet(sprite_path: String) -> void:
	if not ResourceLoader.exists(sprite_path):
		push_warning("CharacterNode: 精灵表缺失 — %s，使用回退颜色" % sprite_path)
		_create_fallback_sprite()
		return

	_sprite_sheet = load(sprite_path)
	if _sprite_sheet == null:
		push_warning("CharacterNode: 无法加载精灵表 — %s" % sprite_path)
		_create_fallback_sprite()
		return

	var frames := SpriteFrames.new()

	# 为四个方向创建 idle 和 walk 动画
	for dir_name: String in DIRECTION_MAP:
		var col: int = DIRECTION_MAP[dir_name]

		# idle 动画：第0行的单帧
		var idle_anim := "idle_" + dir_name
		frames.add_animation(idle_anim)
		frames.set_animation_speed(idle_anim, 1.0)
		frames.set_animation_loop(idle_anim, true)
		var idle_tex := _extract_frame(col, 0)
		if idle_tex:
			frames.add_frame(idle_anim, idle_tex)

		# walk 动画：第1行和第2行的两帧
		var walk_anim := "walk_" + dir_name
		frames.add_animation(walk_anim)
		frames.set_animation_speed(walk_anim, 6.0)
		frames.set_animation_loop(walk_anim, true)
		var walk_a := _extract_frame(col, 1)
		var walk_b := _extract_frame(col, 2)
		if walk_a:
			frames.add_frame(walk_anim, walk_a)
		if walk_b:
			frames.add_frame(walk_anim, walk_b)

	# 移除 SpriteFrames 自带的默认动画（如果存在）
	if frames.has_animation("default"):
		frames.remove_animation("default")

	_body.sprite_frames = frames
	_body.play("idle_down")


## 从精灵表中提取指定位置 (col, row) 的 32x32 帧作为 AtlasTexture。
func _extract_frame(col: int, row: int) -> AtlasTexture:
	if _sprite_sheet == null:
		return null
	var atlas := AtlasTexture.new()
	atlas.atlas = _sprite_sheet
	atlas.region = Rect2(
		col * FRAME_SIZE.x,
		row * FRAME_SIZE.y,
		FRAME_SIZE.x,
		FRAME_SIZE.y
	)
	return atlas


## 精灵表缺失时，创建纯色方块作为回退。
func _create_fallback_sprite() -> void:
	var img := Image.create(FRAME_SIZE.x, FRAME_SIZE.y, false, Image.FORMAT_RGBA8)
	img.fill(character_color)

	# 画一个简单的轮廓使其更可辨识
	var border_color := character_color.darkened(0.3)
	for px in range(FRAME_SIZE.x):
		img.set_pixel(px, 0, border_color)
		img.set_pixel(px, FRAME_SIZE.y - 1, border_color)
	for py in range(FRAME_SIZE.y):
		img.set_pixel(0, py, border_color)
		img.set_pixel(FRAME_SIZE.x - 1, py, border_color)

	var tex := ImageTexture.create_from_image(img)

	var frames := SpriteFrames.new()
	# 为所有方向创建相同的单帧动画
	for dir_name: String in DIRECTION_MAP:
		var idle_name := "idle_" + dir_name
		frames.add_animation(idle_name)
		frames.set_animation_speed(idle_name, 1.0)
		frames.set_animation_loop(idle_name, true)
		frames.add_frame(idle_name, tex)

		var walk_name := "walk_" + dir_name
		frames.add_animation(walk_name)
		frames.set_animation_speed(walk_name, 6.0)
		frames.set_animation_loop(walk_name, true)
		frames.add_frame(walk_name, tex)

	if frames.has_animation("default"):
		frames.remove_animation("default")

	_body.sprite_frames = frames
	_body.play("idle_down")


# ════════════════════════════════════════════════════════════
#  数据更新
# ════════════════════════════════════════════════════════════

## 从服务器数据更新角色状态。
## data 键: "x", "y", "name", "color", "energy", "mood", "last_action",
##          "is_processing", "goal", "npc_id"/"player_id"
func update_from_data(data: Dictionary) -> void:
	var new_x: int = data.get("x", grid_pos.x)
	var new_y: int = data.get("y", grid_pos.y)

	# 位置更新
	if grid_pos != Vector2i(new_x, new_y):
		grid_pos = Vector2i(new_x, new_y)
		target_pos = Vector2(new_x * TILE_PX + TILE_PX / 2.0, new_y * TILE_PX + TILE_PX / 2.0)

	# 处理中状态
	is_processing = data.get("is_processing", false)

	# 心情更新
	var mood_str: String = data.get("mood", "")
	if mood_str != _mood_text:
		set_mood(mood_str)

	# 名字标签（如果后端有更新）
	var new_name: String = data.get("name", "")
	if not new_name.is_empty() and new_name != character_name:
		character_name = new_name
		if _name_label:
			_name_label.text = new_name


## 设置心情图标。
func set_mood(mood: String) -> void:
	_mood_text = mood
	if _mood_indicator == null:
		return

	if mood.is_empty():
		_mood_indicator.visible = false
		return

	# 查找匹配的心情关键词
	var icon_name: String = ""
	for keyword: String in MOOD_ICONS:
		if mood.to_lower().contains(keyword):
			icon_name = MOOD_ICONS[keyword]
			break

	if icon_name.is_empty():
		# 未知心情 — 默认 neutral
		icon_name = MOOD_ICONS.get("neutral", "mood_neutral")

	var icon_path := MOOD_ICON_DIR + icon_name + ".png"
	if ResourceLoader.exists(icon_path):
		var icon_tex: Texture2D = load(icon_path)
		if icon_tex:
			_mood_indicator.texture = icon_tex
			# 缩放到 16x16
			var tex_size := icon_tex.get_size()
			if tex_size.x > 0 and tex_size.y > 0:
				_mood_indicator.scale = Vector2(16.0 / tex_size.x, 16.0 / tex_size.y)
			_mood_indicator.visible = true
			return

	# 图标缺失 — 隐藏
	_mood_indicator.visible = false


# ════════════════════════════════════════════════════════════
#  每帧处理：平滑移动 + 动画
# ════════════════════════════════════════════════════════════

func _process(delta: float) -> void:
	# 闪烁计时器（处理中状态）
	_blink_timer += delta

	# 如果尚未设置目标位置，直接跳到网格位置
	if target_pos == Vector2.ZERO and grid_pos != Vector2i.ZERO:
		target_pos = Vector2(
			grid_pos.x * TILE_PX + TILE_PX / 2.0,
			grid_pos.y * TILE_PX + TILE_PX / 2.0
		)
		position = target_pos

	var distance := position.distance_to(target_pos)

	if distance > 1.0:
		# 平滑移动
		var direction_vec := (target_pos - position).normalized()
		var step := move_speed * delta
		if step >= distance:
			position = target_pos
		else:
			position += direction_vec * step

		# 根据移动方向确定面向
		_update_direction_from_vector(direction_vec)

		if not _is_moving:
			_is_moving = true
			_play_walk_animation()
	else:
		# 已到达目标
		position = target_pos
		if _is_moving:
			_is_moving = false
			_play_idle_animation()

	# z_index 基于 y 坐标，实现正确的前后遮挡
	z_index = int(position.y)
	if is_player:
		z_index += 1  # 玩家始终在同层 NPC 前面

	# 处理中 alpha 闪烁
	if is_processing:
		var alpha := 0.5 + 0.5 * sin(_blink_timer * PROCESSING_BLINK_SPEED)
		modulate.a = alpha
	else:
		modulate.a = 1.0


## 根据移动向量更新面向方向。
func _update_direction_from_vector(dir: Vector2) -> void:
	var new_dir: String
	# 优先选取绝对值较大的分量
	if absf(dir.x) > absf(dir.y):
		new_dir = "right" if dir.x > 0 else "left"
	else:
		new_dir = "down" if dir.y > 0 else "up"

	if new_dir != _current_direction:
		_current_direction = new_dir
		if _is_moving:
			_play_walk_animation()
		else:
			_play_idle_animation()


func _play_walk_animation() -> void:
	if _body and _body.sprite_frames:
		var anim_name := "walk_" + _current_direction
		if _body.sprite_frames.has_animation(anim_name):
			_body.play(anim_name)


func _play_idle_animation() -> void:
	if _body and _body.sprite_frames:
		var anim_name := "idle_" + _current_direction
		if _body.sprite_frames.has_animation(anim_name):
			_body.play(anim_name)


# ════════════════════════════════════════════════════════════
#  绘制（选中高亮）
# ════════════════════════════════════════════════════════════

func _draw() -> void:
	if is_selected:
		# 金色光圈
		draw_arc(Vector2.ZERO, SELECTION_RADIUS, 0, TAU, 32, SELECTION_COLOR, 2.0)
		# 半透明填充
		draw_circle(Vector2.ZERO, SELECTION_RADIUS, Color(SELECTION_COLOR, 0.12))


# ════════════════════════════════════════════════════════════
#  输入处理：点击/双击
# ════════════════════════════════════════════════════════════

func _input_event(_viewport: Viewport, event: InputEvent, _shape_idx: int) -> void:
	# 此方法仅在有 CollisionShape 时触发 — 见下方 _make_clickable
	pass


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		# 检查点击是否在角色区域内
		var local_pos := to_local(get_global_mouse_position())
		if local_pos.length() <= SELECTION_RADIUS:
			if event.button_index == MOUSE_BUTTON_LEFT:
				if event.double_click:
					character_double_clicked.emit(character_id)
				else:
					character_clicked.emit(character_id)
				get_viewport().set_input_as_handled()


# ════════════════════════════════════════════════════════════
#  工具方法
# ════════════════════════════════════════════════════════════

## 瞬移到指定网格位置（无动画）。
func teleport_to(gx: int, gy: int) -> void:
	grid_pos = Vector2i(gx, gy)
	target_pos = Vector2(gx * TILE_PX + TILE_PX / 2.0, gy * TILE_PX + TILE_PX / 2.0)
	position = target_pos
