# R077-A — Independent original-synthetic source contact capability falsifier

Authority: private R009 #23, public #272. Source is frozen public R074 #637 commit `895a6057bd87fe11b3bfa3c2cf6712f2d3d49e4d`, from the original fictional Aster/Juniper generator, **not** protected Naomi/Alison.

Pure stdlib parser and 10 adversarial tests inspect actual generated glTF2 binary. It requires two original actors, independent 17-joint skins, exact source 72-frame 12fps clocks and converging root tracks, but refuses to infer biomechanical contact or naturalness. It reports the missing named heel/toe articulation and universal lack of actual force, collision, slip and scene-floor proof. Even a forged "toe" node does not change HOLD. Both valid source HOLD and invalid source fail closed with CLI exit **12**. The GHA consumer must explicitly expect and inspect the typed source HOLD receipt; no green process exit can be mistaken for actual foot-contact acceptance.

Independent public hosted CPU jobs run tests and original GLB/negative validation. No private assets, paid API, model weights, local actor, new scheduler, merge or release. Keep binary inputs in disposable runner; only tiny source-only JSON evidence has 3-day retention. Reconcile actual native provider results to private #23 and public #272, preserving first RED and exact SHA.

Run: `cd research/r077-r009-source-contact && python3 -m unittest -v test_source_capability`. Source experiment: `python3 qualification/original_reusable_characters/generate_original_glb.py --out /tmp/r077-original.glb --receipt /tmp/r077-producer.json`, then `python3 research/r077-r009-source-contact/source_capability.py --glb /tmp/r077-original.glb --out /tmp/r077-source.json`.
