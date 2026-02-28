class_name UIManager
extends Control
## Central UI orchestrator. Manages all UI panels: show/hide/toggle with smooth
## transitions, and creates the dark tarot theme applied to every child.
##
## Panel categories:
##   HUD        (always visible) : top_bar, mini_map, god_panel, narrative_panel
##   SidePanel  (toggle)         : right-side tabbed panel
##   Overlay    (modal)          : dialogue, character_detail
##   Floating                    : talk_bar

# ── Theme Colors ──
const COLOR_BG_DARK       := Color("#0a0a14")
const COLOR_BG_PANEL      := Color("#14141eea")
const COLOR_BG_LIGHTER    := Color("#1a1a2e")
const COLOR_TEXT_PRIMARY   := Color("#e0e0e8")
const COLOR_TEXT_SECONDARY := Color("#8888a0")
const COLOR_ACCENT_GOLD    := Color("#c8a832")
const COLOR_ACCENT_GREEN   := Color("#4ecca3")
const COLOR_ACCENT_RED     := Color("#e94560")
const COLOR_ACCENT_PURPLE  := Color("#9c27b0")
const COLOR_ACCENT_BLUE    := Color("#2196f3")
const COLOR_ACCENT_ORANGE  := Color("#f5a623")
const COLOR_BORDER_DARK    := Color("#2a2a3e")

## Registered panels: name → Control node
var panels: Dictionary = {}
## Currently active modal overlay name (empty string when none)
var active_overlay: String = ""

signal panel_toggled(panel_name: String, visible: bool)


func _ready() -> void:
	# Stretch to fill the entire viewport
	set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	# Build and apply theme
	_create_theme()


# ── Theme Creation ──

func _create_theme() -> Theme:
	var t := Theme.new()

	# ─ PanelContainer ─
	var panel_style := StyleBoxFlat.new()
	panel_style.bg_color = COLOR_BG_PANEL
	panel_style.border_color = COLOR_BORDER_DARK
	panel_style.set_border_width_all(1)
	panel_style.set_corner_radius_all(6)
	panel_style.set_content_margin_all(8)
	t.set_stylebox("panel", "PanelContainer", panel_style)

	# ─ Button: normal ─
	var btn_normal := StyleBoxFlat.new()
	btn_normal.bg_color = COLOR_BG_LIGHTER
	btn_normal.border_color = Color("#3a3a4e")
	btn_normal.set_border_width_all(1)
	btn_normal.set_corner_radius_all(4)
	btn_normal.set_content_margin_all(6)
	t.set_stylebox("normal", "Button", btn_normal)

	# Button: hover
	var btn_hover := btn_normal.duplicate()
	btn_hover.bg_color = Color("#2a2a3e")
	btn_hover.border_color = COLOR_ACCENT_GOLD
	t.set_stylebox("hover", "Button", btn_hover)

	# Button: pressed
	var btn_pressed := btn_normal.duplicate()
	btn_pressed.bg_color = Color("#3a3a4e")
	btn_pressed.border_color = COLOR_ACCENT_GOLD
	t.set_stylebox("pressed", "Button", btn_pressed)

	# Button: disabled
	var btn_disabled := btn_normal.duplicate()
	btn_disabled.bg_color = Color("#101020")
	btn_disabled.border_color = Color("#1a1a2e")
	t.set_stylebox("disabled", "Button", btn_disabled)

	# Button: focus (keyboard navigation)
	var btn_focus := btn_normal.duplicate()
	btn_focus.border_color = COLOR_ACCENT_BLUE
	btn_focus.set_border_width_all(2)
	t.set_stylebox("focus", "Button", btn_focus)

	# ─ Button colors ─
	t.set_color("font_color", "Button", COLOR_TEXT_PRIMARY)
	t.set_color("font_hover_color", "Button", COLOR_ACCENT_GOLD)
	t.set_color("font_pressed_color", "Button", COLOR_ACCENT_GOLD)
	t.set_color("font_disabled_color", "Button", COLOR_TEXT_SECONDARY)

	# ─ Label ─
	t.set_color("font_color", "Label", COLOR_TEXT_PRIMARY)

	# ─ RichTextLabel ─
	t.set_color("default_color", "RichTextLabel", COLOR_TEXT_PRIMARY)

	# ─ TabContainer: selected tab ─
	var tab_selected := StyleBoxFlat.new()
	tab_selected.bg_color = COLOR_BG_LIGHTER
	tab_selected.set_border_width_all(0)
	tab_selected.border_width_bottom = 2
	tab_selected.border_color = COLOR_ACCENT_GOLD
	tab_selected.set_corner_radius_all(0)
	tab_selected.set_content_margin_all(6)
	t.set_stylebox("tab_selected", "TabContainer", tab_selected)
	t.set_stylebox("tab_selected", "TabBar", tab_selected)

	# TabContainer: unselected tab
	var tab_unselected := StyleBoxFlat.new()
	tab_unselected.bg_color = COLOR_BG_DARK
	tab_unselected.set_border_width_all(0)
	tab_unselected.set_content_margin_all(6)
	t.set_stylebox("tab_unselected", "TabContainer", tab_unselected)
	t.set_stylebox("tab_unselected", "TabBar", tab_unselected)

	# TabContainer: hovered tab
	var tab_hovered := StyleBoxFlat.new()
	tab_hovered.bg_color = Color("#1e1e32")
	tab_hovered.set_border_width_all(0)
	tab_hovered.border_width_bottom = 1
	tab_hovered.border_color = COLOR_TEXT_SECONDARY
	tab_hovered.set_content_margin_all(6)
	t.set_stylebox("tab_hovered", "TabContainer", tab_hovered)
	t.set_stylebox("tab_hovered", "TabBar", tab_hovered)

	# TabContainer: panel background
	var tab_panel := StyleBoxFlat.new()
	tab_panel.bg_color = COLOR_BG_PANEL
	tab_panel.border_color = COLOR_BORDER_DARK
	tab_panel.set_border_width_all(1)
	tab_panel.border_width_top = 0
	tab_panel.set_corner_radius_all(0)
	tab_panel.corner_radius_bottom_left = 6
	tab_panel.corner_radius_bottom_right = 6
	tab_panel.set_content_margin_all(4)
	t.set_stylebox("panel", "TabContainer", tab_panel)

	# Tab font colors
	t.set_color("font_selected_color", "TabContainer", COLOR_ACCENT_GOLD)
	t.set_color("font_unselected_color", "TabContainer", COLOR_TEXT_SECONDARY)
	t.set_color("font_hovered_color", "TabContainer", COLOR_TEXT_PRIMARY)
	t.set_color("font_selected_color", "TabBar", COLOR_ACCENT_GOLD)
	t.set_color("font_unselected_color", "TabBar", COLOR_TEXT_SECONDARY)
	t.set_color("font_hovered_color", "TabBar", COLOR_TEXT_PRIMARY)

	# ─ LineEdit ─
	var le_normal := StyleBoxFlat.new()
	le_normal.bg_color = COLOR_BG_DARK
	le_normal.border_color = COLOR_BORDER_DARK
	le_normal.set_border_width_all(1)
	le_normal.set_corner_radius_all(4)
	le_normal.set_content_margin_all(4)
	t.set_stylebox("normal", "LineEdit", le_normal)

	var le_focus := le_normal.duplicate()
	le_focus.border_color = COLOR_ACCENT_GOLD
	t.set_stylebox("focus", "LineEdit", le_focus)

	t.set_color("font_color", "LineEdit", COLOR_TEXT_PRIMARY)
	t.set_color("font_placeholder_color", "LineEdit", COLOR_TEXT_SECONDARY)
	t.set_color("caret_color", "LineEdit", COLOR_ACCENT_GOLD)
	t.set_color("selection_color", "LineEdit", Color(COLOR_ACCENT_GOLD, 0.25))

	# ─ SpinBox inherits LineEdit ─

	# ─ CheckButton / CheckBox ─
	t.set_color("font_color", "CheckButton", COLOR_TEXT_PRIMARY)
	t.set_color("font_hover_color", "CheckButton", COLOR_ACCENT_GOLD)
	t.set_color("font_color", "CheckBox", COLOR_TEXT_PRIMARY)

	# ─ VScrollBar ─
	var scroll_bg := StyleBoxFlat.new()
	scroll_bg.bg_color = COLOR_BG_LIGHTER
	scroll_bg.set_corner_radius_all(3)
	t.set_stylebox("scroll", "VScrollBar", scroll_bg)

	var grabber := StyleBoxFlat.new()
	grabber.bg_color = Color("#3a3a4e")
	grabber.set_corner_radius_all(3)
	t.set_stylebox("grabber", "VScrollBar", grabber)

	var grabber_hl := grabber.duplicate()
	grabber_hl.bg_color = Color("#4a4a5e")
	t.set_stylebox("grabber_highlight", "VScrollBar", grabber_hl)

	var grabber_pressed := grabber.duplicate()
	grabber_pressed.bg_color = COLOR_ACCENT_GOLD
	t.set_stylebox("grabber_pressed", "VScrollBar", grabber_pressed)

	# ─ HScrollBar (same style) ─
	t.set_stylebox("scroll", "HScrollBar", scroll_bg.duplicate())
	t.set_stylebox("grabber", "HScrollBar", grabber.duplicate())
	t.set_stylebox("grabber_highlight", "HScrollBar", grabber_hl.duplicate())
	t.set_stylebox("grabber_pressed", "HScrollBar", grabber_pressed.duplicate())

	# ─ HSeparator ─
	var sep_style := StyleBoxFlat.new()
	sep_style.bg_color = COLOR_BORDER_DARK
	sep_style.set_content_margin_all(0)
	sep_style.content_margin_top = 4
	sep_style.content_margin_bottom = 4
	t.set_stylebox("separator", "HSeparator", sep_style)

	var vsep_style := StyleBoxFlat.new()
	vsep_style.bg_color = COLOR_BORDER_DARK
	vsep_style.set_content_margin_all(0)
	vsep_style.content_margin_left = 4
	vsep_style.content_margin_right = 4
	t.set_stylebox("separator", "VSeparator", vsep_style)

	# ─ ProgressBar ─
	var prog_bg := StyleBoxFlat.new()
	prog_bg.bg_color = COLOR_BG_DARK
	prog_bg.border_color = COLOR_BORDER_DARK
	prog_bg.set_border_width_all(1)
	prog_bg.set_corner_radius_all(3)
	t.set_stylebox("background", "ProgressBar", prog_bg)

	var prog_fill := StyleBoxFlat.new()
	prog_fill.bg_color = COLOR_ACCENT_GREEN
	prog_fill.set_corner_radius_all(3)
	t.set_stylebox("fill", "ProgressBar", prog_fill)

	# ─ OptionButton ─
	t.set_stylebox("normal", "OptionButton", btn_normal.duplicate())
	t.set_stylebox("hover", "OptionButton", btn_hover.duplicate())
	t.set_stylebox("pressed", "OptionButton", btn_pressed.duplicate())
	t.set_stylebox("disabled", "OptionButton", btn_disabled.duplicate())
	t.set_color("font_color", "OptionButton", COLOR_TEXT_PRIMARY)
	t.set_color("font_hover_color", "OptionButton", COLOR_ACCENT_GOLD)

	# ─ HSlider ─
	var slider_style := StyleBoxFlat.new()
	slider_style.bg_color = COLOR_BORDER_DARK
	slider_style.set_corner_radius_all(2)
	slider_style.content_margin_top = 2
	slider_style.content_margin_bottom = 2
	t.set_stylebox("slider", "HSlider", slider_style)

	var slider_fill := slider_style.duplicate()
	slider_fill.bg_color = COLOR_ACCENT_GOLD
	t.set_stylebox("grabber_area", "HSlider", slider_fill)
	t.set_stylebox("grabber_area_highlight", "HSlider", slider_fill)

	# ─ PopupMenu (for OptionButton dropdowns) ─
	var popup_style := StyleBoxFlat.new()
	popup_style.bg_color = COLOR_BG_DARK
	popup_style.border_color = COLOR_BORDER_DARK
	popup_style.set_border_width_all(1)
	popup_style.set_corner_radius_all(4)
	popup_style.set_content_margin_all(4)
	t.set_stylebox("panel", "PopupMenu", popup_style)

	var popup_hover := StyleBoxFlat.new()
	popup_hover.bg_color = Color("#2a2a3e")
	popup_hover.set_corner_radius_all(2)
	t.set_stylebox("hover", "PopupMenu", popup_hover)

	t.set_color("font_color", "PopupMenu", COLOR_TEXT_PRIMARY)
	t.set_color("font_hover_color", "PopupMenu", COLOR_ACCENT_GOLD)

	# ─ TooltipPanel ─
	var tooltip_style := StyleBoxFlat.new()
	tooltip_style.bg_color = Color("#1a1a2eee")
	tooltip_style.border_color = COLOR_ACCENT_GOLD
	tooltip_style.set_border_width_all(1)
	tooltip_style.set_corner_radius_all(4)
	tooltip_style.set_content_margin_all(6)
	t.set_stylebox("panel", "TooltipPanel", tooltip_style)
	t.set_color("font_color", "TooltipLabel", COLOR_TEXT_PRIMARY)

	# Apply to self — propagates to all children
	self.theme = t
	return t


# ── Panel Registration & Management ──

func register_panel(panel_name: String, panel_node: Control) -> void:
	panels[panel_name] = panel_node


func unregister_panel(panel_name: String) -> void:
	panels.erase(panel_name)
	if active_overlay == panel_name:
		active_overlay = ""


func show_panel(panel_name: String) -> void:
	if not panels.has(panel_name):
		push_warning("UIManager: 未注册的面板 '%s'" % panel_name)
		return
	var panel: Control = panels[panel_name]
	panel.modulate.a = 0.0
	panel.visible = true
	var tween := create_tween()
	tween.tween_property(panel, "modulate:a", 1.0, 0.2).set_ease(Tween.EASE_OUT)
	panel_toggled.emit(panel_name, true)


func hide_panel(panel_name: String) -> void:
	if not panels.has(panel_name):
		return
	var panel: Control = panels[panel_name]
	if not panel.visible:
		return
	var tween := create_tween()
	tween.tween_property(panel, "modulate:a", 0.0, 0.15).set_ease(Tween.EASE_IN)
	tween.tween_callback(func(): panel.visible = false)
	panel_toggled.emit(panel_name, false)


func toggle_panel(panel_name: String) -> void:
	if not panels.has(panel_name):
		push_warning("UIManager: 未注册的面板 '%s'" % panel_name)
		return
	if panels[panel_name].visible:
		hide_panel(panel_name)
	else:
		show_panel(panel_name)


func is_panel_visible(panel_name: String) -> bool:
	if not panels.has(panel_name):
		return false
	return panels[panel_name].visible


# ── Overlay (modal) Management ──

func show_overlay(panel_name: String) -> void:
	# Hide currently active overlay first, then show the new one
	if not active_overlay.is_empty() and panels.has(active_overlay):
		hide_panel(active_overlay)
	active_overlay = panel_name
	show_panel(panel_name)


func hide_overlay() -> void:
	if not active_overlay.is_empty():
		hide_panel(active_overlay)
		active_overlay = ""


func has_active_overlay() -> bool:
	return not active_overlay.is_empty()


# ── Input Handling ──

func _unhandled_input(event: InputEvent) -> void:
	# Close active overlay on Escape
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_ESCAPE and has_active_overlay():
			hide_overlay()
			get_viewport().set_input_as_handled()
