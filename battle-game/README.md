# Battle Game Starter (Godot 4)

An original crowd-battle action game prototype: one hero against waves of enemies,
with a 4-hit combo and a chargeable special attack. Built for Godot 4.3+, with
on-screen touch controls for iPhone/iPad.

## Run it
1. Install Godot 4.3 or newer from https://godotengine.org
2. In the Godot Project Manager, click **Import** and select `project.godot` in this folder.
3. Press **F5** to play.

## Controls
| Action  | Keyboard | Touch                        |
|---------|----------|------------------------------|
| Move    | WASD     | Drag on the left half        |
| Attack  | J        | ATK button                   |
| Special | K        | SP button (when bar is full) |

## Files
- `main.gd`: builds the battlefield, camera, UI, touch joystick and enemy spawning
- `player.gd`: movement, combo attacks, special attack, health
- `enemy.gd`: chase/attack AI, knockback and hit flash

## Export to iOS
Needs a Mac with Xcode. In Godot: **Editor → Manage Export Templates** to download
templates, then **Project → Export → Add → iOS**, set your Apple Team ID, export,
and open the generated project in Xcode to run it on your device.

## Next steps
1. Game feel: hit-stop, screen shake, sound effects
2. Real character models and animations (e.g. Mixamo + AnimationPlayer)
3. Enemy officers, bases to capture, win/lose objectives
4. Performance for bigger crowds (simpler AI, MultiMeshInstance3D)
