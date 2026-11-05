# R009 original fictional character — source-bound heading alignment candidate

**Purpose.** Two self-authored skinned fictional characters have local forward `-Z` while the authored park approach root translation is along world `+/-X`. Root-only static yaw corrects this obvious screen-orientation defect without touching the source animation binary, mesh, skins, materials, textures, frame clock or source bytes. No human identity/rights/biomechanics/PBR approval is implied.

Run with stdlib Python 3.11+:

```sh
python -m unittest -v test_heading_overlay
python heading_overlay.py --input original-source.glb --output heading-aligned-review.glb --receipt heading-receipt.json --expected-sha256 <EXACT_INPUT_SHA256>
```

Scope: fail closed on non-original/third-party source, mismatched SHA, already-rotated root, missing translation, ambiguous roots, wrong skins, malformed GLB and source/output collision. Output is a distinct new file, never in-place.

**Actual Drive-bound 2026-11-05 evidence:** Original topology-clean pair (SHA256 `b9edbafd306fe7b89300628c8bd04298026d0d0ad606fb17dc96ca864dc7136c`) yielded a separate 72f/12fps/960x540 two-view heading-aligned preview and independently rehydrated Drive-byte receipts in owner-only [Batch02](https://drive.google.com/drive/folders/1XIJ-tLgX3nfNxs98bXKyOaxpfZaPPlfY). Independent shoe-sole geometric near-floor proxy at 0.08m/frame remains FAIL: **95/131 before → 89/131 after**. Orientation improved; gait/foot contact still fails. Render/sole witness is a separate CPU VTK scientific observer, not a native Blender source qualification.

**Provenance and custody.** Do not commit any Naomi/Alison protected source, Renderpeople vendor original, or third-party GLB. Public source file is harmless fictional-original utility only. Large GLB/media belongs to owner-private Drive; public Git/DLE holds source, test and metadata. No public workflow or release permission is authorized here. Existing source PR #271 remains a separate single-writer producer, no direct edits; owner review is necessary before accepting this independent candidate.

**Quality next:** convert source local hip/knee/ankle and heel/ball/toe semantics to contact-aware gait; measure source-native full 72×2×2 foot trajectories and geometry with independent observers. Do not mark model ready for natural gait on heading change or green source-only tests.
