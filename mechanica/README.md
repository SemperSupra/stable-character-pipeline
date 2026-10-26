# Mechanical Systems — articulated public Go prototypes

**Status:** synthetic mechanical blockouts, not production CAD, photoreal renders, validated vehicle physics, or a released asset library.

The public standalone Go generator exports a real articulated glTF/GLB file, plus a joint/rig manifest. Its keyframes move separate geometry around explicit pivots; these are **not static models**.

| Rig | Articulation |
| --- | --- |
| Ground SUV | Four independently hinged side doors, tailgate, front steering joints, four wheel axles |
| Twin-prop aircraft | Propellers, port/starboard flaps, ailerons, retracting landing gear, elevator, rudder |
| Orbital spacecraft | Two deploying solar-array yokes, gimballed RCS thrusters, docking hatch, antenna pan |
| Original Iron Atlas giant mech | Jointed hips, knees, ankles, torso, cockpit, shoulders, elbows, cannon assembly, independently hinged claw fingers, elevating pods, sensors and maintenance hatch |

Run from the mechanica directory with Go 1.23+:

~~~sh
go test -count=1 ./...
go test -race -count=1 ./...
go vet ./...
go run . -out out
~~~

The output files are mechanical_scene.glb, mechanical_scene.gltf, mechanical_scene.bin and rig_manifest.json, in out/. Open the GLB in Blender or a glTF animation viewer and play the articulation-8s animation. Scene convention is X-forward, Y-lateral, Z-up converted by one root to glTF Y-up.

The manifest includes semantic joint names, pivot-node indices, axes and declarative angle bounds. Stock glTF players interpolate animations but **do not enforce** these bounds at runtime. Continuous rotation is densely sampled to avoid quaternion reversal.

This is self-authored synthetic geometry, not imported source CAD or any human-character material. No secrets, tokens, networked Go modules or private workcell dependencies. Independent mechanical and Flora/Fauna workcells can later compose scenes via a reviewed scene adapter, not by copying private source.

**Remaining gates:** verify public GitHub Actions run and outputs; add Blender CPU movie/contact sheet, joint collision/limits/contact falsifiers, parametric variants, physical solvers, interactive controls and three-audience user experience. No human integration, merge, publication license, or production release is implied.


## Iron Atlas heavy walker (original fictional vehicle)

The fourth independent rig is `titan/iron-atlas`, in `titan.go`. It is a stylized technical blockout, not a MechWarrior franchise asset or a physically credible weapons design. A keyed eight-second sequence exercises the torso, hip/knee/ankle joints, cockpit, articulated arm and manipulator, elevation mechanisms, hatch, and sensors. Hip/keyframe motion is **not** a solved walking gait or a ground-contact demonstration. Realtime safety limits/IK and collision detection are still missing.

The CPU renderer accepts `--focus all` (composite scene) and `--focus titan` (closer articulated mech view). CI generates MP4 + contact sheet for both. The public Actions download expires; durable preview publication to a separate public review branch is restricted to same-repository feature-branch push builds, never untrusted PRs. Review artifacts before using them as production demonstrations.
