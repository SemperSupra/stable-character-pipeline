# Independent synthetic PCM acoustic observer — research, not biological classification

This [respiratory/vocal DLE #582](https://github.com/SemperSupra/stable-character-pipeline/issues/582) batch independently analyzes WAV bytes rendered by the 17-original synthetic source family [draft PR #584](https://github.com/SemperSupra/stable-character-pipeline/pull/584). It is a **separate original Go 1.23 stdlib-only package** that reads source-neutral 48kHz mono 16-bit canonical WAVs, not generator state or identity metadata; validates declared RIFF/PCM fields, size/cap, clipping and silence.

`AnalyzeWAV` exposes actual numeric RMS, peak, mean, 20ms-window RMS, fraction of total energy in the first 20ms and `∑(x[i]−x[i−1])²/[4∑x[i]²]`: a bounded **roughness proxy**, NOT a calibrated spectral centroid or measurement of human nasal/oral anatomy. `EvidenceAt` measures coherent energy at one **prescribed, caller-specified frequency** over the first 250ms. It labels high candidate line support as `coherent_line_present_uncalibrated` and otherwise **abstains**; a single bin cannot determine a true F0 or rule out missing fundamental/overtone ambiguity. The original private pitch-command 160Hz versus earlier L0 estimate 80Hz remains unresolved and cannot be inferred from synthetic test fixtures.

Test families include all 17 generated examples (16 audible + 1 deliberately silent), deterministic source-neutral observation, synthetic noise route differences (nasal smoother than oral in *this* proxy), increased energy for increased prescribed flow, transient early energy on non-pulmonary beatbox clicks, coherent line evidence on the synthetic hum/lip-whistle and abstention on nonpitched breath/click/silence. An independent numerical sine/noise oracle tests non-overfit line discrimination. Tests reject noncanonical WAV headers, 44.1kHz, invalid data length, truncation, near-clipping and impossible spectral frequency arguments. These are synthetic **algorithm qualification only**, not validation of real breath or instrument sound or a human singing voice.

Run from `research/respiratory-vocal`:

```sh
go test -race -count=1 ./...
go vet ./...
go run ./cmd/respiratory-audio-critic
```

The CLI emits a machine-readable report for the original 17 fixture-generated WAVs; no WAV artifact is uploaded, copied from donors or stored in Git. **Independent external source physics** remains to be compared: nasal/oral phase acoustics ([bioacoustic phase study](https://pubmed.ncbi.nlm.nih.gov/21956580/)), nonstationary breath sound characteristics ([respiratory sound analysis review](https://pmc.ncbi.nlm.nih.gov/articles/PMC2990233/)) and spectral/time-frequency analysis ([oral/nasal sounds review](https://www.mdpi.com/2079-9292/14/10/1994)). None of these data are included or asserted to establish the current proxy's realism.

**Holds:** source-specific independent FFT/multiresolution oracle, human/noise data ethics/consent/rights, masked A/B perceptual or false-pitch study, native private engine source, 2D/3D breathing deformation, human+assistive/agent DX and actual real-device latency. No private GHA, automatic merges, releases or deployments.
