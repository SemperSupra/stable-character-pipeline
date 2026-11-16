# Unified Respiratory–Vocal Performance — source-neutral contracts, research only

This is the **independent first executable batch** for [DLE #582](https://github.com/SemperSupra/stable-character-pipeline/issues/582), subordinate to coupled respiration [#528](https://github.com/SemperSupra/stable-character-pipeline/issues/528), core Physical Vocal [#143](https://github.com/SemperSupra/stable-character-pipeline/issues/143), Voice Workbench [#526](https://github.com/SemperSupra/stable-character-pipeline/issues/526) and automated critics [#521](https://github.com/SemperSupra/stable-character-pipeline/issues/521). Uses Go 1.23 **standard library only**. It is **NOT** integrated with or a substitute for private original `physicalvocal.v0`, the 21 unchanged historic WAV fixtures, real anatomy/physiology, recorded voice identity, human speech or production wind instruments.

## Contract `respiratory.performance.v0`

`behavior.Performance`: `classification`, `action`, fixed `sample_rate_hz=48000`, and nonoverlapping, contiguous `Frame` intervals in sample units. Each frame has explicit **inspiration/expiration/pause**, separate signed branch volume flows (`nasal_flow_m3_s`, `oral_free_flow_m3_s`, `external_port_flow_m3_s`) and total signed volume flow in m³/s, subglottal gauge pressure in Pa, velopharyngeal and mouth free-opening flags, external port classification and up to eight independently typed acoustic sources. Positive volume flow means outward/expiratory, negative means inward/inspiratory. Separately expose prescribed source oscillator Hz vs independently measured F0. The source kind has no direct emotional/medical diagnosis semantics.

Flow conservation: **`Q_total = Q_nasal + Q_oral_free + Q_external_port`**; each branch must agree with phase, physical path and valve state. A tube on the mouth is a *distinct outlet* from free-mouth flow, not an additional copy of the same air. Non-pulmonary lip/tongue percussive clicks may occur during a no-flow pause; lip whistling requires a free oral jet; flute/whistle edge tone and reed tone require a corresponding external port. Singing/humming is not a pressure-only sound effect. Cry/laughter/scream are behavior orchestration events; the low-level model only validates source and acoustic topology.

The model intentionally avoids presenting synthetic flow rates or pressure values as safe/unsafe physiological thresholds. Signed pressure, airflow and route remain independent; airflow does not dictate psychology, exercise status or respiratory injury. 2D/3D anatomy, object material dynamics, pulmonic effort state, true gas composition and acoustic propagation are future source-bound adapters.

## Independent bats, tests and admission

```sh
cd research/respiratory-vocal
go test -race -count=1 ./...
go vet ./...
```

Positive fixture coverage: nasal, oral, mixed inhale/outflow, pant with alternating flow, humming (nasal voiced), singing, lip whistling, non-pulmonary beatbox click, flute/edge jet, reed, blown object whistle, elastic balloon inflation, external straw suction, crying/sobbing style, laughter, scream. Negative controls: invalid timing, unknown action/source/port, wrong flow signs, branch-conservation, velum/mouth seal mismatch, oral-vs-nasal route, object coupling mismatches, misleading oscillator tags, invalid NaN/Inf, protected/non-synthetic classification and missing phase transitions.

**Not yet implemented**: actual respiration/breath sounds, 48kHz WAV renderer, acoustic waveform physics, phase/amplitude/nasal filter calibration, dynamic multi-path acoustic waves, multi-pressure solver, source-specific vocal fold self-oscillation, real instrument excitation, preapproved scientific sound corpus training, inverse physiology, HIL hearing or calibrated respiratory diagnosis. These are separate follow-on gates and must not be represented as completed.

## Human / assistive / automation / agent consumers

The same `Performance` should feed Go CLI, native GUI, REST/JSON API, novice prompt and touch/2D anatomy controls; all operate on **canonical state and validated operations**. For novice UX distinguish "breath quietly," "pant," "hum," "whistle with lips," "blow whistle," "play flute," "blow balloon," "sip through a straw": they activate different flow/physical source mechanisms. Advanced users get temporal phase, airway route and source physics; status and limitations available to humans using assistive technology and agents. Internationalization requirements: English/German/Thai.

Preserve exact private original audio fixture checksums, private #72 and the owner-gated 60 private GHA minutes. This public branch is original synthetic-only; do not fetch protected recordings, donor code/weights or private engine source into free public Actions. No merge/release/deployment until owner acceptance.
