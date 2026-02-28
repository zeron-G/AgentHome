extends Node
## Manages local client settings that persist across sessions.
## Uses ConfigFile → user://settings.cfg
## Registered as autoload singleton "SettingsManager".
##
## Sections:
##   [display] - window_mode, ui_scale, vsync
##   [audio]   - master_volume, music_volume, sfx_volume, muted
##   [game]    - show_thoughts, auto_scroll_events, minimap_zoom
##   [network] - server_url, auto_reconnect, reconnect_delay_sec
##   [controls]- (future key_bindings)

const SAVE_PATH := "user://settings.cfg"

var config: ConfigFile = ConfigFile.new()

## Default values per section. Used as fallbacks when key is missing.
var defaults: Dictionary = {
	"display": {
		"window_mode": 0,       # 0=windowed, 1=fullscreen, 2=borderless
		"ui_scale": 1.0,
		"vsync": true,
	},
	"audio": {
		"master_volume": 0.8,
		"music_volume": 0.7,
		"sfx_volume": 0.8,
		"muted": false,
	},
	"game": {
		"show_thoughts": true,
		"auto_scroll_events": true,
		"minimap_zoom": 1.0,
	},
	"network": {
		"server_url": "ws://localhost:8000/ws",
		"auto_reconnect": true,
		"reconnect_delay_sec": 3.0,
	},
}

signal setting_changed(section: String, key: String, value: Variant)


func _ready() -> void:
	load_settings()


func load_settings() -> void:
	var err := config.load(SAVE_PATH)
	if err != OK:
		# First run — populate with defaults and persist
		_apply_defaults()
		save_settings()


func save_settings() -> void:
	var err := config.save(SAVE_PATH)
	if err != OK:
		push_warning("SettingsManager: 保存设置失败, 错误码: %d" % err)


func get_setting(section: String, key: String, default: Variant = null) -> Variant:
	# Use built-in defaults when available; caller may override with `default` arg
	var fallback: Variant = default
	if defaults.has(section) and defaults[section].has(key):
		fallback = defaults[section][key]
	return config.get_value(section, key, fallback)


func set_setting(section: String, key: String, value: Variant) -> void:
	config.set_value(section, key, value)
	save_settings()
	setting_changed.emit(section, key, value)


func has_setting(section: String, key: String) -> bool:
	return config.has_section_key(section, key)


## Resets one section to its defaults. Pass "" to reset all.
func reset_section(section: String = "") -> void:
	if section.is_empty():
		for sec in defaults:
			_reset_single_section(sec)
	else:
		_reset_single_section(section)
	save_settings()


func _reset_single_section(section: String) -> void:
	if not defaults.has(section):
		return
	for key in defaults[section]:
		config.set_value(section, key, defaults[section][key])
		setting_changed.emit(section, key, defaults[section][key])


func _apply_defaults() -> void:
	for section in defaults:
		for key in defaults[section]:
			if not config.has_section_key(section, key):
				config.set_value(section, key, defaults[section][key])


## Apply display settings to the engine. Call after changing display section.
func apply_display_settings() -> void:
	var win_mode: int = get_setting("display", "window_mode")
	match win_mode:
		0:
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
		1:
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
		2:
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
			DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_BORDERLESS, true)

	var vsync_on: bool = get_setting("display", "vsync")
	if vsync_on:
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED)
	else:
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)

	var ui_scale: float = get_setting("display", "ui_scale")
	# Clamp to sane range
	ui_scale = clampf(ui_scale, 0.5, 3.0)
	get_tree().root.content_scale_factor = ui_scale


## Apply audio settings to the audio buses. Call after changing audio section.
func apply_audio_settings() -> void:
	var master_bus := AudioServer.get_bus_index("Master")
	if master_bus < 0:
		return

	var muted: bool = get_setting("audio", "muted")
	AudioServer.set_bus_mute(master_bus, muted)

	var master_vol: float = get_setting("audio", "master_volume")
	master_vol = clampf(master_vol, 0.0, 1.0)
	AudioServer.set_bus_volume_db(master_bus, linear_to_db(master_vol))

	# Music bus (if exists)
	var music_bus := AudioServer.get_bus_index("Music")
	if music_bus >= 0:
		var music_vol: float = get_setting("audio", "music_volume")
		AudioServer.set_bus_volume_db(music_bus, linear_to_db(clampf(music_vol, 0.0, 1.0)))

	# SFX bus (if exists)
	var sfx_bus := AudioServer.get_bus_index("SFX")
	if sfx_bus >= 0:
		var sfx_vol: float = get_setting("audio", "sfx_volume")
		AudioServer.set_bus_volume_db(sfx_bus, linear_to_db(clampf(sfx_vol, 0.0, 1.0)))


## Convenience: get the server URL from network settings.
func get_server_url() -> String:
	return get_setting("network", "server_url")
