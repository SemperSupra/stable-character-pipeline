# Passive external-object boundary — research qualification

Independent original Go 1.23 standard-library model for [Physical Vocal respiratory DLE #582](https://github.com/SemperSupra/stable-character-pipeline/issues/582). Stacked on the 17-mode synthetic WAV [draft PR #584](https://github.com/SemperSupra/stable-character-pipeline/pull/584), **without editing the original renderer, its sample checksums or the private original Physical Vocal engine/21 WAV hashes**.

## Contract

This is a **lumped prescribed-flow boundary impedance oracle**, not an instrument generator. The performance event has an external-port frame with signed volumetric flow `Q` in m³/s, positive exhaling from the person and negative through a straw toward the person. Fixed resistance `R` has SI units Pa·s/m³; pressure drop `Δp_R=R Q`; irreversible dissipation per frame `E_R=R Q² Δt ≥0`.

Five distinct source-neutral port types are admitted: flute edge, reed, external whistle, elastic balloon, straw. Flute/reed/whistle/straw remain **resistance-only** in this model and do **not** sound like the physical instrument: there is no distributed bore, mouthpiece reed/jet oscillation, transient wave reflection, resonator impedance, air inertia or actual inhalation physiology. They are separate ports so an instrument model can later supply these mechanisms without pretending that a flute edge equals a reed oscillator.

The *balloon only* adds a simple **linear compliance research proxy** with air volume `V` and pressure `P_elastic=V/C`; `dV/dt = Q`, stored energy `U(V)=V²/(2C)`. Midpoint pressure yields an exact discrete accounting identity `P_total Q Δt = R Q² Δt + [U(V_next)−U(V_previous)]`. This is **not** a real balloon membrane constitutive relation (which can be nonlinear/hysteretic), or a medical pressure safety threshold. Reject capacity overflow, negative/nonfinite R/C, invalid port/route coupling, unsupported arbitrary object and silence/no-port masquerading as musical airflow. Single-port flow only; multiport pressure feedback is a later state-version change.

Run offline from `research/respiratory-vocal`:

```sh
go test -race -count=1 ./...
go vet ./...
go run ./cmd/external-port-bakeoff
```

The CLI emits **five strictly synthetic numeric receipts**, not source WAVs, user/person recordings, or private assets. Test coverage: five fixture families, negative straw suction sign, increased resistance vs power loss, increasing balloon volume/pressure and work accounting over two frames, provenance/classification admission, nonfinite/capacity/port rejection and deterministic replay.

For independently sourced physical prior art: frequency-dependent input impedance distinguishes wind-instrument bores and reed mouthpieces (e.g. [University of Edinburgh, instrument wave propagation](https://era.ed.ac.uk/bitstream/handle/1842/27572/VanWalstijnM_2002redux.pdf?isAllowed=y&sequence=1); [UCDavis acoustics chapter](https://www.math.ucdavis.edu/~saito/data/auditory/gough_musical-acoustics.pdf)). No donor code/assets copied; any physical instrument model needs pinned revision/license and independent empirical/spectral checks.

**Holds:** no native private Physical Vocal source integration, actual wind-instrument audibility or physiological fit, real balloon stress/compliance, straw drag from real flow and pressure, streaming stateful acoustic interaction or human hearing/AT acceptance. No new private GHA minutes. No automatic merge/release/deploy.
