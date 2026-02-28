class_name DayNightCycle
extends CanvasModulate
## 昼夜循环系统。根据时间阶段和季节对世界颜色进行渐变调色。

# ---- 时间阶段颜色 ----
const PHASE_COLORS: Dictionary = {
	"dawn":  Color(1.0, 0.92, 0.82),   # 温暖橙白 — 黎明
	"day":   Color(1.0, 1.0, 1.0),     # 中性白 — 白天
	"dusk":  Color(0.92, 0.72, 0.62),  # 暖红橙 — 黄昏
	"night": Color(0.42, 0.42, 0.72),  # 深蓝 — 夜晚
}

# ---- 季节色温叠加 ----
const SEASON_TINTS: Dictionary = {
	"spring": Color(0.95, 1.0, 0.92),  # 微暖绿 — 春
	"summer": Color(1.0, 0.95, 0.88),  # 暖热 — 夏
	"autumn": Color(1.0, 0.92, 0.85),  # 冷橙 — 秋
	"winter": Color(0.9, 0.92, 1.0),   # 冷白蓝 — 冬
}

var current_phase: String = "day"
var current_season: String = "spring"
var target_color: Color = Color.WHITE
var transition_speed: float = 2.0


func _ready() -> void:
	color = Color.WHITE
	_update_target_color()


## 设置时间阶段（"dawn", "day", "dusk", "night"）
func set_time_phase(phase: String) -> void:
	if not PHASE_COLORS.has(phase):
		push_warning("DayNightCycle: 未知时间阶段 '%s'，忽略。" % phase)
		return
	current_phase = phase
	_update_target_color()


## 设置季节（"spring", "summer", "autumn", "winter"）
func set_season(season: String) -> void:
	if not SEASON_TINTS.has(season):
		push_warning("DayNightCycle: 未知季节 '%s'，忽略。" % season)
		return
	current_season = season
	_update_target_color()


## 同时设置时间阶段和季节（避免两次更新）
func set_time_and_season(phase: String, season: String) -> void:
	if PHASE_COLORS.has(phase):
		current_phase = phase
	if SEASON_TINTS.has(season):
		current_season = season
	_update_target_color()


## 根据当前阶段和季节计算目标颜色（阶段色 * 季节色温）
func _update_target_color() -> void:
	var phase_color: Color = PHASE_COLORS.get(current_phase, Color.WHITE)
	var season_tint: Color = SEASON_TINTS.get(current_season, Color.WHITE)
	# 分量相乘实现叠加调色
	target_color = Color(
		phase_color.r * season_tint.r,
		phase_color.g * season_tint.g,
		phase_color.b * season_tint.b,
		1.0
	)


func _process(delta: float) -> void:
	# 平滑插值过渡到目标颜色
	color = color.lerp(target_color, delta * transition_speed)
