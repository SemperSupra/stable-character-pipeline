# R033 — grounded visual observation receipt (source-safe structural contract)

Authority: private [R033 #168](https://github.com/SemperSupra/stable-character-pipeline-private/issues/168) and public [Visual-QA V1 #150](https://github.com/SemperSupra/stable-character-pipeline/issues/150). This is **not a VLM model, an image generator, a 3D measurement system, or a gallery**. It defines a fail-closed evidence boundary between sovereign model-generated descriptions and independent source geometry, video, and CPE acceptance.

## Why
The local BigMac actor has independently documented a first live two-render description smoke through multimodal `llama-server`; there is still no qualified multiview, temporal, blind observation→CPE discrepancy→corrective edit loop. This source-only contract avoids turning an attractive but unverified caption into model, geometry, identity, owner preference, or cinematic acceptance.

Each observation ties one model+prompt version, approved media source SHA, camera identity, decoded frame numbers and individual frame SHAs to a visible region and a distinct `direct|inferred|unknown` assertion. The receipt status is **always** `OBSERVATIONS_UNVERIFIED` and `canonical=false`. A typed/syntactic pass cannot verify media bytes, model weights, rights, source scene, semantic correctness, or actual viewpoint. Those require a second independent checker with admitted artifacts.

Image receipts hold exactly one decoded frame; video receipts require rational timebase and allow time-indexed observations. A behavior/motion claim requires at least two distinct frames. A single image cannot establish walking, gait or activity over time. Confidence values are explicitly *uncalibrated model-reported scores* if present; unknown assertions cannot carry a positive score.

## Offline build/test
```sh
cd research/r033-observer-contract
GOPROXY=off GOTOOLCHAIN=local go test -race -count=1 ./...
GOPROXY=off GOTOOLCHAIN=local go vet ./...
GOPROXY=off GOTOOLCHAIN=local go run ./cmd/check < examples/public_synthetic_fixture.json
```

The example uses **invented digest strings** and synthetic metadata only; it does not prove an image or model was ever generated. GitHub Actions runs source-only tests on public free CPU, with no private model, media, tokens, weights, network API, or real person.

## Next integration gates
1. Real local R033 observer must derive SHA256 of original image/clip, exact decoded frame pixels, scene-camera version, model weights/mmproj, prompt and source-admission receipt; never accept only an asserted hash.
2. Blind multiview/per-region captioning, image landmarks and 3D geometric oracle produce independent receipts; a source mismatch or absent evidence yields HOLD. Media/identity and private source stay on approved BigMac/TrueNAS private custody.
3. Join to CPE concept hypotheses only *after observation*, with `OBSERVED/INFERRED/UNKNOWN`; compare to requested targets separately. Never infer actual body proportions from VLM prose when precise geometry is available.
4. Add read-only annotation views to the already deployed private tailnet gallery; no external CDN or media upload.
5. Maintain three audiences: concise observations for humans, versioned JSON receipts for automation, and executable immutable DLE/source-state for agents.

No new GitHub registry, scheduler, source/rights authority, or canonical promotion is implied.
