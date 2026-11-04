# Original-source native MIT weighted-foot observation

Source producer: draft #274 exact HEAD `8307fb98a1e47083a657a708d27b2ea4420f4b2a`. Reuses *only* its existing immutable public-original MIT research ZIP artifact `13305643308` (whole ZIP SHA256 `2bbf1036744e4fcd614cd207bc9e9eb2147b943f59c53d9de7dff1b324320204`) and original editable Blender scene SHA256 `2e5c5fcc826c95d200b06cc2dcd22138944102426a86f1f683689ae458aff7ab`. Nothing writes or resaves source.

## Native observation
Blender 4.5.15 reads actual 80-bone imported rig and evaluates all 72 source frames. For each of two actor roots and two feet, select vertices with combined real imported foot/toe vertex-group weights at least 0.5, then calculate actual world-space min Z and XY centroid. Measure displacement only over consecutive near-ground frames (height from actual scene ground top in [-7,+3.5] cm); threshold for possible slide is 8 cm/frame at 12fps. A missing source group, empty region, mesh, clock, or digest fails closed. No contact window yields UNKNOWN rather than false PASS.

The observer does **not** certify actual contact, kinematic joint coordinate systems, rest-axis calibration, bio gait, two-camera visual acceptance, actor identity, or any private source. Independent original eight synthetic negative/positive tests run first; the native run produces JSON evidence for human, automation CLI and read-only agent audiences. Preserve all rights/source-writer/runner/CPE/merge/release/deploy holds; source stays OPEN/DRAFT.

Run the non-native unit tests from this folder with `python3 -m unittest -v test_observer`. Run native only with original verified Blender and correct source ZIP; no paid/private cloud or protected Naomi/Alison media.
