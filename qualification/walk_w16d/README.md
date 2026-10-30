# W16-D independent source-only 3D geometry falsifiers

Workcell origin: walking owner #84, based on exact typed W16-A #114 head 0b283718183dff20313c3ba4517830245267c053. Two abstract self-authored original actors on exact synthetic 12/1 timestamps, glTF right-handed Y-up, no private assets or sovereign data. No W14/W15/actual integrated-walk claim.

Source-only computational primitives and independent hostile tests: heel/toe planted ground/hover/penetration and 3D displacement; a continuous swept relative-motion two-body sphere minimum-distance invariant that rejects midpoint crossings despite collision-free endpoints; strict pole/knee side; camera pinhole frustum and foreground proxy sphere occlusion; adversarial timestamps, rights, role spoofing, NaN, clipping and per-segment stance contact.

The synthetic scene tolerance gates are NEWLY DECLARED: sole vertical magnitude <=1e-4; continuous stance heel/toe drift <=1e-3; proxy actor sphere radius 0.25, source units. These are not validated anthropometric or physical-force gates and are not inherited W14 vertex tolerances. The CLI receipt reports NegativeControls=0 because Go tests, not the CLI, execute fifteen mutation tests; CI is the native witness. Camera is a simple pinhole and collisions use proxy spheres, **not actual mesh collision/occlusion**. Visibility of a root proxy is not proof of full person visibility.

Reproduction: cd qualification/walk_w16d; GO111MODULE=off go vet . ; GO111MODULE=off go test -race -v . ; GO111MODULE=off go run . forward forward.json ; python3 check_receipt.py forward forward.json. The outward profile is analogous.

To qualify actual W16-C skin: feed the same typed source frame/rig vertex semantics through this checker with independently observed animated surface geometry, and review/contact threshold choice. No release, merge, rights/CPE promotion, paid CI or private media operations.
