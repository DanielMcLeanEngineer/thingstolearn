class_name Enemy
extends CharacterBody3D

signal defeated

const SPEED := 3.0
const GRAVITY := 20.0
const ATTACK_RANGE := 1.8
const ATTACK_COOLDOWN := 2.0
const DAMAGE := 5.0
const BASE_COLOR := Color(0.7, 0.25, 0.2)

var hp := 30.0
var target: Player
var attack_timer := randf_range(0.5, ATTACK_COOLDOWN)
var stun_timer := 0.0
var knockback := Vector3.ZERO
var mat: StandardMaterial3D


func _ready() -> void:
	add_to_group("enemies")

	var shape := CollisionShape3D.new()
	shape.shape = CapsuleShape3D.new()
	add_child(shape)

	var mesh := MeshInstance3D.new()
	mesh.mesh = CapsuleMesh.new()
	mat = StandardMaterial3D.new()
	mat.albedo_color = BASE_COLOR
	mesh.material_override = mat
	add_child(mesh)


func _physics_process(delta: float) -> void:
	if stun_timer > 0:
		# Knocked back after being hit
		stun_timer -= delta
		velocity.x = knockback.x
		velocity.z = knockback.z
		knockback = knockback.lerp(Vector3.ZERO, 8.0 * delta)
	elif is_instance_valid(target) and target.hp > 0:
		var to_target := target.global_position - global_position
		to_target.y = 0
		var dist := to_target.length()
		if dist > 0.01:
			rotation.y = atan2(-to_target.x, -to_target.z)
		if dist > ATTACK_RANGE:
			velocity.x = to_target.x / dist * SPEED
			velocity.z = to_target.z / dist * SPEED
		else:
			velocity.x = 0
			velocity.z = 0
			attack_timer -= delta
			if attack_timer <= 0:
				attack_timer = ATTACK_COOLDOWN
				target.take_damage(DAMAGE)
	else:
		velocity.x = 0
		velocity.z = 0

	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	move_and_slide()


func take_hit(damage: float, direction: Vector3) -> void:
	if hp <= 0:
		return  # already defeated this frame
	hp -= damage
	stun_timer = 0.3
	knockback = direction * 6.0
	# Flash white when hit
	mat.albedo_color = Color.WHITE
	create_tween().tween_property(mat, "albedo_color", BASE_COLOR, 0.15)
	if hp <= 0:
		defeated.emit()
		queue_free()
