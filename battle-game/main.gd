extends Node3D

const MAX_ENEMIES := 40  # raise this for bigger battles (watch iPhone performance)
const CAMERA_OFFSET := Vector3(0, 9, 11)

var player: Player
var camera: Camera3D
var ko_count := 0
var hp_bar: ProgressBar
var special_bar: ProgressBar
var ko_label: Label
var message_label: Label

# On-screen joystick for touch screens
var joystick_touch_index := -1
var joystick_start := Vector2.ZERO
var joystick_vector := Vector2.ZERO


func _ready() -> void:
	_setup_input()
	_build_world()
	_build_ui()
	for i in MAX_ENEMIES:
		_spawn_enemy()


func _setup_input() -> void:
	_add_key("move_left", KEY_A)
	_add_key("move_right", KEY_D)
	_add_key("move_up", KEY_W)
	_add_key("move_down", KEY_S)
	_add_key("attack", KEY_J)
	_add_key("special", KEY_K)


func _add_key(action: String, key: Key) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action)
	var event := InputEventKey.new()
	event.physical_keycode = key
	InputMap.action_add_event(action, event)


func _build_world() -> void:
	# Ground
	var ground := StaticBody3D.new()
	var ground_shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(200, 1, 200)
	ground_shape.shape = box
	ground_shape.position.y = -0.5
	ground.add_child(ground_shape)
	var ground_mesh := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(200, 200)
	ground_mesh.mesh = plane
	var ground_mat := StandardMaterial3D.new()
	ground_mat.albedo_color = Color(0.45, 0.4, 0.3)
	ground_mesh.material_override = ground_mat
	ground.add_child(ground_mesh)
	add_child(ground)

	# Lighting and sky colour
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, 30, 0)
	sun.shadow_enabled = true
	add_child(sun)
	var world_env := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.6, 0.75, 0.9)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.5, 0.5, 0.5)
	world_env.environment = env
	add_child(world_env)

	# Player
	player = Player.new()
	player.position = Vector3(0, 1, 0)
	player.died.connect(_on_player_died)
	add_child(player)

	# Camera follows from behind and above
	camera = Camera3D.new()
	camera.position = player.position + CAMERA_OFFSET
	add_child(camera)
	camera.look_at(player.position)


func _build_ui() -> void:
	var ui := CanvasLayer.new()
	add_child(ui)

	hp_bar = _make_bar(ui, Vector2(20, 20), Color(0.85, 0.2, 0.2), Player.MAX_HP)
	special_bar = _make_bar(ui, Vector2(20, 55), Color(1.0, 0.8, 0.1), Player.MAX_SPECIAL)

	ko_label = Label.new()
	ko_label.position = Vector2(20, 90)
	ko_label.add_theme_font_size_override("font_size", 28)
	ui.add_child(ko_label)

	message_label = Label.new()
	message_label.set_anchors_preset(Control.PRESET_CENTER)
	message_label.add_theme_font_size_override("font_size", 48)
	ui.add_child(message_label)

	# Touch buttons, bottom-right of the screen
	var attack_button := _make_button(ui, "ATK", -200, -200)
	attack_button.button_down.connect(player.request_attack)
	var special_button := _make_button(ui, "SP", -380, -140)
	special_button.button_down.connect(player.start_special)


func _make_bar(parent: Node, pos: Vector2, color: Color, max_value: float) -> ProgressBar:
	var bar := ProgressBar.new()
	bar.position = pos
	bar.size = Vector2(300, 26)
	bar.max_value = max_value
	bar.show_percentage = false
	var fill := StyleBoxFlat.new()
	fill.bg_color = color
	bar.add_theme_stylebox_override("fill", fill)
	parent.add_child(bar)
	return bar


func _make_button(parent: Node, text: String, left: float, top: float) -> Button:
	var button := Button.new()
	button.text = text
	button.add_theme_font_size_override("font_size", 32)
	button.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	button.offset_left = left
	button.offset_top = top
	button.offset_right = left + 150
	button.offset_bottom = top + 150
	parent.add_child(button)
	return button


func _spawn_enemy() -> void:
	var enemy := Enemy.new()
	var angle := randf() * TAU
	var distance := randf_range(12.0, 25.0)
	enemy.position = player.position + Vector3(cos(angle), 0, sin(angle)) * distance
	enemy.position.y = 1
	enemy.target = player
	enemy.defeated.connect(_on_enemy_defeated)
	add_child(enemy)


func _on_enemy_defeated() -> void:
	ko_count += 1
	player.add_special(5.0)
	call_deferred("_spawn_enemy")  # keep the battlefield full


func _on_player_died() -> void:
	message_label.text = "DEFEATED - %d KOs" % ko_count
	player.set_physics_process(false)
	await get_tree().create_timer(3.0).timeout
	get_tree().reload_current_scene()


func _process(delta: float) -> void:
	var target := player.global_position + CAMERA_OFFSET
	camera.global_position = camera.global_position.lerp(target, 5.0 * delta)
	camera.look_at(player.global_position + Vector3(0, 1, 0))

	player.touch_move = joystick_vector
	hp_bar.value = player.hp
	special_bar.value = player.special
	ko_label.text = "KO: %d" % ko_count


func _input(event) -> void:
	# Left half of the screen acts as a virtual joystick
	if event is InputEventScreenTouch:
		var half_width := get_viewport().get_visible_rect().size.x / 2.0
		if event.pressed and joystick_touch_index == -1 and event.position.x < half_width:
			joystick_touch_index = event.index
			joystick_start = event.position
		elif not event.pressed and event.index == joystick_touch_index:
			joystick_touch_index = -1
			joystick_vector = Vector2.ZERO
	elif event is InputEventScreenDrag and event.index == joystick_touch_index:
		joystick_vector = ((event.position - joystick_start) / 80.0).limit_length(1.0)
