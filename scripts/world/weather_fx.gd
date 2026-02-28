class_name WeatherFX
extends Node2D
## 天气粒子特效系统。根据后端天气状态切换晴天 / 雨天 / 暴风雨视觉效果。

var current_weather: String = "sunny"

# ---- 子节点 ----
var rain_particles: GPUParticles2D
var lightning_timer: Timer
var flash_overlay: ColorRect

# ---- 闪电参数 ----
var _flash_tween: Tween = null
const LIGHTNING_INTERVAL_MIN: float = 2.0
const LIGHTNING_INTERVAL_MAX: float = 6.0
const LIGHTNING_FLASH_CHANCE: float = 0.6  ## 每次定时器触发时闪电的概率


func _ready() -> void:
	# ---- 创建雨滴粒子节点 ----
	rain_particles = GPUParticles2D.new()
	rain_particles.emitting = false
	rain_particles.amount = 200
	rain_particles.lifetime = 1.5
	rain_particles.z_index = 90  # 绘制在大多数游戏对象之上

	# 粒子材质
	var mat := ParticleProcessMaterial.new()
	mat.direction = Vector3(0.3, 1.0, 0.0)
	mat.spread = 15.0
	mat.initial_velocity_min = 200.0
	mat.initial_velocity_max = 400.0
	mat.gravity = Vector3(0.0, 400.0, 0.0)
	mat.scale_min = 0.8
	mat.scale_max = 1.2

	# 发射区域 — 覆盖视口上方宽矩形
	mat.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	mat.emission_box_extents = Vector3(800.0, 10.0, 0.0)

	# 颜色：蓝白色雨滴
	mat.color = Color(0.75, 0.85, 1.0, 0.7)

	rain_particles.process_material = mat

	# 尝试加载雨滴纹理，若不存在则使用默认白色粒子
	var rain_tex_path := "res://resources/art/particles/rain_drop.png"
	if ResourceLoader.exists(rain_tex_path):
		rain_particles.texture = load(rain_tex_path)

	# 粒子在摄像机空间绘制（跟随摄像机而非世界）
	rain_particles.position = Vector2(0.0, -300.0)  # 从上方发射

	add_child(rain_particles)

	# ---- 闪电定时器 ----
	lightning_timer = Timer.new()
	lightning_timer.one_shot = true
	lightning_timer.timeout.connect(_on_lightning_timer)
	add_child(lightning_timer)

	# ---- 闪电闪光覆盖层 ----
	flash_overlay = ColorRect.new()
	flash_overlay.color = Color(1.0, 1.0, 1.0, 0.0)
	flash_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	flash_overlay.z_index = 100
	# 覆盖足够大的区域
	flash_overlay.size = Vector2(1600.0, 1200.0)
	flash_overlay.position = Vector2(-800.0, -600.0)
	add_child(flash_overlay)


## 设置天气状态
func set_weather(weather: String) -> void:
	if weather == current_weather:
		return
	current_weather = weather

	match weather:
		"sunny":
			_stop_rain()
			_stop_lightning()
		"rainy":
			_start_rain(200, 200.0, 400.0)
			_stop_lightning()
		"storm":
			_start_rain(400, 300.0, 600.0)
			_start_lightning()
		_:
			# 未知天气按晴天处理
			_stop_rain()
			_stop_lightning()


func _start_rain(amount: int, vel_min: float, vel_max: float) -> void:
	rain_particles.amount = amount
	var mat: ParticleProcessMaterial = rain_particles.process_material as ParticleProcessMaterial
	if mat:
		mat.initial_velocity_min = vel_min
		mat.initial_velocity_max = vel_max
	rain_particles.emitting = true


func _stop_rain() -> void:
	rain_particles.emitting = false


func _start_lightning() -> void:
	_schedule_next_lightning()


func _stop_lightning() -> void:
	lightning_timer.stop()
	# 清除残余闪光
	flash_overlay.color.a = 0.0
	if _flash_tween and _flash_tween.is_valid():
		_flash_tween.kill()


func _schedule_next_lightning() -> void:
	var wait := randf_range(LIGHTNING_INTERVAL_MIN, LIGHTNING_INTERVAL_MAX)
	lightning_timer.start(wait)


func _on_lightning_timer() -> void:
	if current_weather != "storm":
		return

	# 随机概率触发闪电闪光
	if randf() < LIGHTNING_FLASH_CHANCE:
		_do_flash()

	# 安排下次
	_schedule_next_lightning()


func _do_flash() -> void:
	if _flash_tween and _flash_tween.is_valid():
		_flash_tween.kill()

	_flash_tween = create_tween()
	# 闪光亮起
	_flash_tween.tween_property(flash_overlay, "color:a", 0.3, 0.05)
	# 保持一瞬
	_flash_tween.tween_interval(0.05)
	# 衰减消失
	_flash_tween.tween_property(flash_overlay, "color:a", 0.0, 0.1)
