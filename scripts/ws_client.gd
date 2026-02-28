extends Node
## WebSocket client with auto-reconnect.

var _ws: WebSocketPeer = WebSocketPeer.new()
var _url: String = ""
var _connected: bool = false
var _retry_count: int = 0
var _retry_timer: float = 0.0
const MAX_RETRY_DELAY: float = 10.0

signal message_received(data: Dictionary)
signal connected
signal disconnected


func connect_to_server(url: String) -> void:
	_url = url
	_retry_count = 0
	_retry_timer = 0.0
	_attempt_connect()


func _attempt_connect() -> void:
	var err = _ws.connect_to_url(_url)
	if err != OK:
		push_error("WebSocket connect error: %d" % err)


func send_json(data: Dictionary) -> void:
	if _connected:
		var json_str = JSON.stringify(data)
		_ws.send_text(json_str)


func is_connected_to_server() -> bool:
	return _connected


func _process(delta: float) -> void:
	_ws.poll()
	var state = _ws.get_ready_state()

	if state == WebSocketPeer.STATE_OPEN:
		if not _connected:
			_connected = true
			_retry_count = 0
			connected.emit()
			GameState.connection_status_changed.emit(true)

		while _ws.get_available_packet_count() > 0:
			var pkt = _ws.get_packet()
			var text = pkt.get_string_from_utf8()
			var json = JSON.new()
			var parse_result = json.parse(text)
			if parse_result == OK:
				message_received.emit(json.data)
			else:
				push_warning("JSON parse error: %s" % json.get_error_message())

	elif state == WebSocketPeer.STATE_CLOSED:
		if _connected:
			_connected = false
			disconnected.emit()
			GameState.connection_status_changed.emit(false)
		# Auto-reconnect with backoff
		_retry_timer -= delta
		if _retry_timer <= 0:
			_retry_count += 1
			_retry_timer = min(_retry_count * 1.5, MAX_RETRY_DELAY)
			_attempt_connect()

	elif state == WebSocketPeer.STATE_CLOSING:
		pass # Wait for close to complete


func close_connection() -> void:
	_ws.close()
	_connected = false
