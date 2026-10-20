class_name Player
extends CharacterBody3D

signal died

const SPEED := 7.0
const GRAVITY := 20.0
const MAX_HP := 200.0
const MAX_SPECIAL := 100.0
# Each combo hit: [damage, reach, arc in degrees, duration in seconds]
const COMBO := [
	[10.0, 2.5, 100.0, 0.25],
	[10.0, 2.5, 100.0, 0.25],
	[15.0, 3.0, 150.0, 0.30],
	[30.0, 3.5, 360.0, 0.50],  # finisher hits all around you
]

var hp := MAX_HP
var special := 0.0
var touch_move := Vector2.ZERO  # set by the on-screen joystick
var facing := Vector3.FORWARD

var combo_step := 0
var combo_window := 0.0
var attack_timer := 0.0
var attack_queued := false
var special_timer := 0.0
var special_tick := 0.0
var invincible_timer := 0.0

var body_mesh: MeshInstance3D
var weapon_pivot: Node3D


func _ready() -> void:
	add_to_group("player")

	var shape := CollisionShape3D.new()
	shape.shape = CapsuleShape3D.new()
	add_child(shape)

	body_mesh = MeshInstance3D.new()
	body_mesh.mesh = CapsuleMesh.new()
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.2, 0.4, 0.9)
	body_mesh.material_override = mat
	add_child(body_mesh)

	# The weapon swings around a "shoulder" pivot
	weapon_pivot = Node3D.new()
	weapon_pivot.position = Vector3(0.4, 0.3, 0)
	body_mesh.add_child(weapon_pivot)
	var weapon := MeshInstance3D.new()
	var blade := BoxMesh.new()
	blade.size = Vector3(0.15, 0.15, 1.8)
	weapon.mesh = blade
	weapon.position = Vector3(0, 0, -0.9)
	weapon_pivot.add_child(weapon)


func _physics_process(delta: float) -> void:
	invincible_timer -= delta
	combo_window -= delta

	if Input.is_action_just_pressed("attack"):
		request_attack()
	if Input.is_action_just_pressed("special"):
		start_special()

	var input := Input.get_vector("move_left", "move_right", "move_up", "move_down")
	if touch_move.length() > 0.1:
		input = touch_move
	var dir := Vector3(input.x, 0, input.y)

	if special_timer > 0:
		_update_special(delta)
	elif attack_timer > 0:
		attack_timer -= delta
		dir = facing * 0.3  # small lunge while swinging
	elif attack_queued:
		_start_attack()

	if dir.length() > 0.1 and attack_timer <= 0:
		facing = dir.normalized()
		rotation.y = atan2(-facing.x, -facing.z)

	velocity.x = dir.x * SPEED
	velocity.z = dir.z * SPEED
	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	move_and_slide()


func request_attack() -> void:
	attack_queued = true  # buffered so mashing feels responsive


func _start_attack() -> void:
	attack_queued = false
	if combo_window <= 0:
		combo_step = 0
	var hit: Array = COMBO[combo_step]
	attack_timer = hit[3]
	combo_window = hit[3] + 0.4
	_hit_enemies(hit[0], hit[1], hit[2])
	_swing_weapon(hit[3])
	combo_step = (combo_step + 1) % COMBO.size()


func start_special() -> void:
	if special >= MAX_SPECIAL and special_timer <= 0:
		special = 0
		special_timer = 2.0
		special_tick = 0


func _update_special(delta: float) -> void:
	special_timer -= delta
	special_tick -= delta
	body_mesh.rotation.y += 20.0 * delta  # spinning attack
	if special_tick <= 0:
		special_tick = 0.15
		_hit_enemies(12.0, 4.5, 360.0)
	if special_timer <= 0:
		body_mesh.rotation.y = 0


func _hit_enemies(damage: float, reach: float, arc_degrees: float) -> void:
	for node in get_tree().get_nodes_in_group("enemies"):
		var enemy := node as Enemy
		var to_enemy := enemy.global_position - global_position
		to_enemy.y = 0
		var dist := to_enemy.length()
		if dist > reach:
			continue
		var direction := to_enemy / dist if dist > 0.01 else facing
		if rad_to_deg(facing.angle_to(direction)) <= arc_degrees / 2.0:
			enemy.take_hit(damage, direction)
			if special_timer <= 0:
				add_special(2.0)


func _swing_weapon(duration: float) -> void:
	weapon_pivot.rotation.y = deg_to_rad(70)
	var tween := create_tween()
	tween.tween_property(weapon_pivot, "rotation:y", deg_to_rad(-70), duration)


func add_special(amount: float) -> void:
	special = min(special + amount, MAX_SPECIAL)


func take_damage(amount: float) -> void:
	if invincible_timer > 0 or special_timer > 0 or hp <= 0:
		return
	hp -= amount
	invincible_timer = 0.5
	if hp <= 0:
		hp = 0
		died.emit()
