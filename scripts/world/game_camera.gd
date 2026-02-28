class_name GameCamera
extends Camera2D
## 游戏摄像机：平滑跟随玩家，支持鼠标滚轮缩放和中键拖拽平移。

# ---- 跟随目标 ----
var follow_target: Node2D = null

# ---- 缩放参数 ----
var target_zoom_level: float = 1.5    ## 默认缩放倍率
var zoom_speed: float = 8.0           ## 缩放插值速度
var min_zoom: float = 0.5
var max_zoom: float = 3.0
var zoom_step: float = 0.15

# ---- 拖拽平移 ----
var _is_dragging: bool = false
var _drag_start_mouse: Vector2 = Vector2.ZERO
var _drag_start_cam: Vector2 = Vector2.ZERO


func _ready() -> void:
	# 平滑跟随
	position_smoothing_enabled = true
	position_smoothing_speed = 5.0

	# 世界边界限制 (20x20 格子, 每格32px = 640px)
	limit_left = 0
	limit_top = 0
	limit_right = 640
	limit_bottom = 640

	# 初始缩放
	zoom = Vector2(target_zoom_level, target_zoom_level)

	make_current()


## 设置跟随目标节点
func set_follow_target(target: Node2D) -> void:
	follow_target = target


func _process(delta: float) -> void:
	# ---- 平滑缩放插值 ----
	var desired_zoom := Vector2(target_zoom_level, target_zoom_level)
	zoom = zoom.lerp(desired_zoom, delta * zoom_speed)

	# ---- 跟随目标位置 (未拖拽时) ----
	if follow_target != null and follow_target.is_inside_tree() and not _is_dragging:
		global_position = follow_target.global_position


func _unhandled_input(event: InputEvent) -> void:
	# ---- 鼠标滚轮缩放 ----
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.pressed:
			if mb.button_index == MOUSE_BUTTON_WHEEL_UP:
				# 放大（zoom 值增大 = 画面放大）
				target_zoom_level = clampf(target_zoom_level + zoom_step, min_zoom, max_zoom)
				get_viewport().set_input_as_handled()
			elif mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
				# 缩小
				target_zoom_level = clampf(target_zoom_level - zoom_step, min_zoom, max_zoom)
				get_viewport().set_input_as_handled()

		# ---- 中键拖拽平移 ----
		if mb.button_index == MOUSE_BUTTON_MIDDLE:
			if mb.pressed:
				_is_dragging = true
				_drag_start_mouse = mb.global_position
				_drag_start_cam = global_position
			else:
				_is_dragging = false

	if event is InputEventMouseMotion and _is_dragging:
		var motion := event as InputEventMouseMotion
		# 鼠标移动方向相反于摄像机移动；除以 zoom 使拖拽速度与缩放一致
		var delta_screen: Vector2 = motion.global_position - _drag_start_mouse
		global_position = _drag_start_cam - delta_screen / zoom
		get_viewport().set_input_as_handled()

	# ---- Home 键回到跟随目标 ----
	if event is InputEventKey:
		var ke := event as InputEventKey
		if ke.pressed and ke.keycode == KEY_HOME:
			if follow_target != null and follow_target.is_inside_tree():
				global_position = follow_target.global_position
			get_viewport().set_input_as_handled()
