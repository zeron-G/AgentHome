class_name GodPanel
extends PanelContainer
## God Agent commentary display — purple italic text with 2px purple border,
## season icon, fade-in animation on updates, and narrative stage indicator.
## Inherits dark tarot theme from UIManager.

var _text: RichTextLabel
var _season_icon: TextureRect
var _stage_label: Label
var _fade_tween: Tween

# Season icon paths
const SEASON_ICONS := {
	"spring": "res://resources/art/ui/season_spring.png",
	"summer": "res://resources/art/ui/season_summer.png",
	"autumn": "res://resources/art/ui/season_autumn.png",
	"winter": "res://resources/art/ui/season_winter.png",
}


func _ready() -> void:
	custom_minimum_size.y = 80

	# ── Purple 2px border via StyleBoxFlat override ──
	var style := StyleBoxFlat.new()
	style.bg_color = Color("#14141eea")
	style.border_color = Color("#9c27b0")
	style.set_border_width_all(2)
	style.set_corner_radius_all(6)
	style.set_content_margin_all(10)
	add_theme_stylebox_override("panel", style)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 6)
	add_child(vbox)

	# ── Top row: season icon + title ──
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 6)
	vbox.add_child(header)

	_season_icon = TextureRect.new()
	_season_icon.custom_minimum_size = Vector2(20, 20)
	_season_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_season_icon.expand_mode = TextureRect.EXPAND_FIT_WIDTH_PROPORTIONAL
	_season_icon.visible = false
	header.add_child(_season_icon)

	var title := Label.new()
	title.text = "神谕"
	title.add_theme_font_size_override("font_size", 13)
	title.add_theme_color_override("font_color", Color("#9c27b0"))
	header.add_child(title)

	# ── Commentary text ──
	_text = RichTextLabel.new()
	_text.bbcode_enabled = true
	_text.text = ""
	_text.append_text("[i][color=#9c27b0]世界在注视之下...[/color][/i]")
	_text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_text.fit_content = true
	vbox.add_child(_text)

	# ── Narrative stage (subtle text at bottom) ──
	_stage_label = Label.new()
	_stage_label.text = ""
	_stage_label.add_theme_font_size_override("font_size", 11)
	_stage_label.add_theme_color_override("font_color", Color("#8888a0"))
	_stage_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	vbox.add_child(_stage_label)

	# Load initial season icon
	_load_season_icon(GameState.god_season)


# ── Public API (backwards compatible) ──

func update_commentary(commentary: String) -> void:
	if not commentary.is_empty():
		_set_commentary_with_fade(commentary)


## New comprehensive update method.
func update_narrative(commentary: String, season: String, stage: int) -> void:
	if not commentary.is_empty():
		_set_commentary_with_fade(commentary)
	_load_season_icon(season)
	if stage > 0:
		_stage_label.text = "叙事阶段: %d" % stage
	else:
		_stage_label.text = ""


# ── Internals ──

func _set_commentary_with_fade(commentary: String) -> void:
	# Cancel any running fade tween
	if _fade_tween and _fade_tween.is_running():
		_fade_tween.kill()

	# Fade out, update, fade in
	_fade_tween = create_tween()
	_fade_tween.tween_property(_text, "modulate:a", 0.0, 0.15)
	_fade_tween.tween_callback(func():
		_text.text = ""
		_text.append_text("[i][color=#9c27b0]%s[/color][/i]" % commentary)
	)
	_fade_tween.tween_property(_text, "modulate:a", 1.0, 0.35).set_ease(Tween.EASE_OUT)


func _load_season_icon(season: String) -> void:
	var path: String = SEASON_ICONS.get(season, "")
	if path.is_empty():
		_season_icon.visible = false
		return
	if ResourceLoader.exists(path):
		_season_icon.texture = load(path)
		_season_icon.visible = true
	else:
		_season_icon.visible = false
