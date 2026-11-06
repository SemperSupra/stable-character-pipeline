# Independent native decoded-audio observer (experimental)

Source DLE: [#293](https://github.com/SemperSupra/stable-character-pipeline/issues/293); cross-cutting [#272](https://github.com/SemperSupra/stable-character-pipeline/issues/272). Independent additive child of immutable audiovisual source [PR #307](https://github.com/SemperSupra/stable-character-pipeline/pull/307) (no edits to original mux or verifier). Go 1.23 stdlib; FFmpeg used only for bounded native decoding. No LLM, VLM, proprietary model, animal recording, or protected source.

## Previously missed falsifier

The parent `verify_av.py` checks WAV hash and H264/AAC stream metadata, but it does not examine *decoded mux audio*. An AAC track containing silence or delayed/unplanned transients can pass metadata checks. This observer independently decodes audio from the actual multiplex, locates audible transient onsets without using planned timing during detection, and compares them to the frozen synthetic event clock. Missing, extra and shifted onsets become a machine-readable FAIL. It also checks duration, source class and exact planned sample clock. One-to-one audible groups are used for simultaneous planned hoofbeats.

```sh
cd qualification/equine/av_observer
go test -race -count=1 ./...
go vet ./...
go run ./cmd/av_observer -events events.json -audio generated.mp4 -receipt decoded.json
```

Successful output is `PASS_SYNTHETIC_TRANSIENT_ALIGNMENT_ONLY`, *never* anatomical hoof contact, animal acoustic realism, hoof identity, stereo placement or biologically validated gait. Current 40ms tolerance, 5ms RMS bins, minimum transient threshold and 80ms refractory apply to **dry original synthetic Foley**; production soundtracks, noisy scenes and close-spaced events must be independently calibrated/qualified. FFmpeg codec priming, pre-echo and runtime versions are measured/recorded; the decoded PCM SHA is in the receipt.

## Governance and cost

The observer earns its keep only if it catches silent, missing, duplicate or shifted encoded sounds not detected by the parent metadata check and does so reproducibly on public CPU with low false positives. The workflow uses pinned, disjoint public source producers (#296 and #297), native AAC, hostile negative controls, short-lived bounded receipts and least privilege. This is **not** deployed, merged or promoted; private materials, rights, main, CPE, runners and releases remain held. Retire it if existing tools gain an equally strong independent measurement at lower integration cost. No new service, DB or permanent infrastructure.

## Measured mesh geometry is a *falsifier*, not contact certification

The independent additive `contact_proxy.go` and `cmd/contact_proxy` consume the original-synthetic 48-frame hoof science report from pinned [PR #298](https://github.com/SemperSupra/stable-character-pipeline/pull/298), the *same GLB bytes* and a pinned expected GLB hash, together with source-original planned gait events. It recomputes near-ground event gaps, skate/penetration and swing screens from the native evaluated 48-frame four-hoof trajectories, refusing mismatched model/clock/hash, forged source thresholds and conflicting scientific verdicts. Its output is **`FAIL_PROXY_CONTRADICTS_PLANNED_AUDIO`** or **`NO_PROXY_CONTRADICTION_CONTACT_UNKNOWN`**. No force sensor, pressure, limb load or validated horse gait is present: no geometric acceptance can certify real contact or animal acoustics. GLB filename and same-run SHA alone do not attest the observer truly evaluated that source; separate native-job provenance and cross-run artifact custody remain required.

The public-native workflow tests this against an independently regenerated actual IK GLB at immutable #302 and the frozen #298 observer. A local or CI failure remains evidence, never rebranded as biomechanical acceptance. No releases, protected references or default-branch promotions.
