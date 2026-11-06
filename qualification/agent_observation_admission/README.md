# SCP read-only original-synthetic observation admission v1

Workcell authority: public original equine DLE #293, human #272 and common agent-fitting experiment PRs #300/#301/#306/#309/#317. This is **a new, independent source-only tool under a disjoint path**, not a replacement for existing synthetic ASF/AMC source family admission [PR #31](https://github.com/SemperSupra/stable-character-pipeline/pull/31). The capture-family isolation concept is reused without importing unknown rights or motion-source assets.

## Interface for humans, automation and reasoning agents
Command: `go run . admit SOURCE_ROOT manifest.json`; discovery: `go run . capabilities`. Output `scp.synthetic_observation_receipt.v1`. Every observation contains a single immutable original synthetic PNG byte SHA256, an upstream source-root SHA256, capture-family ID, camera ID, timestamp in nanoseconds and requested `training` or `heldout` split. Camera and capture-family IDs are declarations; **we do not independently authenticate camera intrinsic/extrinsic parameters or physical capture origin**. Go stdlib only, no model inference, network, remote writes, or arbitrary program execution.

Minimal manifest (replace SHA strings and image paths with actual public-original bytes):

```json
{
 "schema":"scp.synthetic_observations.v1",
 "subject_class":"public_original_synthetic_equine",
 "subject_id":"synthetic_pony_001",
 "rights_class":"original_self_authored_synthetic",
 "observations":[
  {"id":"view_a_001","path":"train_a.png","sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","source_root_sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","capture_family":"capture_train_one","camera_id":"camera_left","frame_time_ns":0,"split":"training"},
  {"id":"view_b_001","path":"train_b.png","sha256":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","source_root_sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","capture_family":"capture_train_one","camera_id":"camera_right","frame_time_ns":0,"split":"training"},
  {"id":"view_c_001","path":"heldout.png","sha256":"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd","source_root_sha256":"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee","capture_family":"capture_heldout_two","camera_id":"camera_forward","frame_time_ns":0,"split":"heldout"}
 ]
}
```

**Hard rejects:** private/person source classes, non-self-authored/public rights, nonlocal/escaped/symlinked paths, oversized/invalid PNGs, SHA mismatches, JSON duplicates/unknown keys and trailing values, duplicate observation or path, duplicate capture/camera/frame tuple, source-root, image-byte or capture-family appearing across training/heldout splits, insufficient observations, or fewer than two declared training cameras.

**Scientific holds:** this proves *only* syntactic capture-family split separation and actual per-image byte custody under the bounded synthetic source manifest. A source submitter can falsify family IDs or source-root SHA; without independent acquisition provenance those declarations are untrusted. This is **not** actual camera calibration, verified external holdout, photogrammetry, actor reasoning, reconstruction, anatomical suitability or private-photo admission. Output explicitly says `CameraIndependence=UNKNOWN_NO_EXTERNAL_CALIBRATION`, `ExternalPhotoAdmission=NOT_RUN`, `ScientificResult=UNKNOWN`. The synthetic PNG tests create original images inside temporary directories; they are not genuine user or subject photos.

## Execution and governance
This PR is independently testable on standard $0 public Actions; it must never ingest private real-person or owned horse image/video media to public GHA. Production protected-lane use requires separate rights and custody admission, cryptographically bound capture-session records, calibrated cameras and verified withheld capture families. A future multiview photo fitter may consume this receipt **only** as a prerequisite, never as proof of image-ground-truth or subject identity. No model mutation/merge/release/CPE authority.

DOPAV per-batch hygiene: exact head, base, source-owner branch, CI first RED, path collisions, artifact SHA custody, duplicate/superseded PRs and next DLE baton. Existing read-only repo hygiene source owner remains #312; no new all-PR inventory created here.
