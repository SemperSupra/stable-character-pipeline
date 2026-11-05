# SCP agent-driven reconstruction: source-bound render-mask metric workcell

**Status:** public-original-synthetic candidate-only numerical observer. This is a standalone module stacked on PR #300, but does not edit its original contract files or canonical producer branches. No GUI or LLM execution occurs here.

## What it does
Read a strict `scp.render_masks.v1` manifest tying a claimed held-out camera/frame and exact canonical model revisions to three source-file SHA256s: reference PNG mask, baseline model rendered PNG mask, and candidate model rendered PNG mask. Decode the real image pixels and return IoU, precision, recall, foreground/union/intersection counts and candidate-vs-baseline IoU delta. Permit explicit `mask_channel: alpha` or `luma` and integer threshold 1–254; report soft-edge pixel counts.

Machine operation: `go run . measure ROOT manifest.json`; discovery: `go run . capabilities`.
- Human: review `scp.render_mask_metrics.v1` JSON and source SHA receipts.
- Automation: same CLI with explicit nonzero error on malformed/stale data.
- Agent: same typed inspect/measure operation, but **no** shell, Blender, arbitrary Python, network, model mutation, or owner promotion capability exposed by this program.

Required input schema example (hashes illustrative placeholders; cannot be used until replaced with actual sha256 bytes):

```json
{
 "schema":"scp.render_masks.v1",
 "experiment_id":"synthetic_pony_silhouette",
 "baseline_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
 "candidate_sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
 "subject_class":"public_original_synthetic_equine",
 "camera_id":"heldout_side",
 "frame_index":12,
 "split":"heldout",
 "mask_channel":"alpha",
 "threshold":128,
 "reference":{"path":"reference.png","sha256":"<replace with real SHA-256>"},
 "baseline_render":{"path":"baseline.png","sha256":"<replace with real SHA-256>"},
 "candidate_render":{"path":"candidate.png","sha256":"<replace with real SHA-256>"}
}
```

## Safety and scientific limits
- Paths must be relative to a specified root and resolved within it; refuse symlink escape and invalid/hacked SHA. Images capped at 8 MiB PNG bytes and 2048×2048 decoded pixels. JSON capped at 1 MiB; reject duplicate or unknown keys, extra values, bad subject class, missing declared heldout split, invalid frame/view, hash mismatches, different dimensions and empty reference masks.
- Exact source hashes are checked, but **the split label, camera metadata and independent-verifier identity are not cryptographically attested**. No unseen-camera guarantee, photometric realism, real anatomy, identity accuracy, 3D reconstruction correctness, or real gait inference. The metrics are a pixel-comparison primitive, not a final model acceptance gate.
- Mask thresholding and anti-aliasing can change IoU. Record explicit channel/threshold and inspect soft edges. Consistent camera, subject, projection and segmentation rules are prerequisites before comparing across character releases. Transparent NRGBA alpha masks are supported.
- The unit tests generate actual public-original synthetic PNG pixels in temp directories; they do **not** read real model renders yet. Native Blender/GHCR source producer and photo/video reference adapters are next workcells. Images or models from private character corpora are never passed to public CI.

## Ownership / next baton
Authoritative public Shetland DLE #293 and original human R009 #272; protected private R009 #23 and release owner gate unchanged. PR #300 is the frozen prerequisite typed experiment proposal contract. This observer can be qualified independently on standard $0 public GitHub Actions. Add a future source-pinned native Blender render harness for 26-joint Shetland and 35-joint humans, with withheld views and source model matching, then a separate skin-strain/anatomy verifier. Only a later authenticated composite receipt may feed PR #300's provisional evaluation. No merge, release, deployment or CPE promotion implied.

Store source/manifest/metrics/test evidence in Git/DLE; source media and model binaries require controlled Drive custody and independent byte rehydration.
