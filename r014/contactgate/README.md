# R014/R009 quarter-frame contact diagnostics — source-safe research draft

This standalone original Go 1.23 stdlib workcell is an **independent negative-control companion** to the current R009 BigMac project-original synthetic ASTER/JUNIPER gait rep and R014 source-motion qualification. The BigMac actor previously reported **72 frames at 12 fps** and visible shoe/contact RED; the project-original scene/video and any private or third-party model are **NOT** in this branch or public CI. This workcell tests a precise *interface and metrics*, not that actual gait or cinematic work.

## Intended inputs

An explicitly admitted local extractor should export **exactly 285 full + quarter-frame observations** (inclusive 0..284 ticks for 72 original whole frames at 12 fps; 4 samples per frame interval). Each observation has an integer tick, root world coordinate, and left/right heel, ball and toe world coordinates. A rights-qualified independent reviewer supplies:
- exact input scene and motion byte SHA-256, rest/world/camera source identity and cold-replay evidence;
- ground plane world normal, plane offset and real metres-per-world-unit calibration;
- independently derived per-foot stance windows, their active support marker (heel/ball/toe), and an authenticated stance-label SHA-256;
- a separately approved policy with maximum penetration, maximum *active-support* hover, maximum active-marker stance sliding speed, and minimum support-window duration, all in physical metres, metres/second, seconds;
- trusted external registry evidence; do not self-mark a candidate as independent.

The current public library explicitly allows **project-original synthetic RDTE** input only and hard-rejects other scopes; its source SHA fields are *identifiers*, NOT authorization to expose raw scene/media to public GHA. The `Trust` record is provided by an external caller and **is not cryptographically authenticated inside this prototype**. A real execution venue must independently inspect provenance, reviewer authority, per-asset rights, signatures and source-byte custody.

## Invariants

- Every quarter-sample, first and last full frames, source rate and frame count are mandatory. Reject reordered or missing observations.
- Ground normal must be a unit vector; conversion to metres is explicit. Report all six marker clearances throughout the complete clip (including swing); do **not** call a raised non-support toe a contact failure.
- Only independently labelled *active support* markers are tested for hover and horizontal sliding. Reject overlaps, missing-foot support, invalid marker labels, and fragments too short to satisfy independently approved minimum duration. Also measure any marker penetrating the ground plane on any sample.
- Compute speed from **consecutive quarter ticks**, not just whole-frame displacement; retain extreme samples. Report world root travel as an observability metric, not a quality pass.
- A threshold violation returns `RED_DECLARED_CONTACT_POLICY`; otherwise the strongest allowed result is `WITHIN_DECLARED_NUMERIC_POLICY_ONLY__NO_PHYSICAL_OR_RELEASE_PASS`. Ground-plane proxies cannot prove pressure, actual foot sole-ground collision, biomechanics, natural gait, or completed two-character cinematic quality.
- Policy SHA is recomputed from the caller-supplied values and matched against an independent trusted record; a candidate cannot silently widen its own numerical thresholds. The example .004 m penetration, .010 m support hover, .05 m/s support speed, .25 sec segment duration are **fictional unit-test thresholds only**, not approved product acceptance criteria.

## Reproduce

`cd r014/contactgate && go test -race -count=1 -v ./... && go vet ./... && go run ./cmd/receipt`

Public/free Actions executes only the fictional 72-frame trajectory in Go tests and archives JSON *source/test identity only*. It does not download or run Blender, CMU, native MHR, Renderpeople, Alison, Naomi, the R009 scene or real local actor pose tracks.

## Next local HIL link (separate approval)

The BigMac actor should use its *admitted* project-original synthetic scene to produce a **private local numeric witness**, ideally at exact whole/quarter ticks with cold-reopen SHA and threshold/stance-label reviewer proof. Compare baseline vs a single reversible correction using identical timebase and input scene. Record before/after contact violation extent and preserve historical REDs. Do not silently export the per-sample trajectory to a public runner, Drive, or this PR without the specific derivative/source admission.

All R009 actual human film, R014 MHR neural correctives, anatomy and skin, Product D1–D4, source rights, canonical CharacterPack and release gates remain HOLD. Draft PR only; no merge or private minutes.
