
## W04 geometry-bound organ receipts (independent botanical qualification)

Use the optional `-organs` argument to emit a deterministic JSON sidecar recording
**exact** per-material vertex/index extents for each generated tube, leaf, petal,
corolla, fruit and disk. The receipt includes typed organ IDs, a provisional
parent attachment inferred from the nearest earlier stem/bark/branch segment,
metric anchor/attachment distance, a SHA-256 of the organ records and an explicit
`attachment_status` that does **not** claim developmental botanical lineage.

```sh
go run ./wildflowers -preset wildflowers/presets/quercus_robur.json \
  -out /tmp/oak.glb -organs /tmp/oak.organs.json
```

The graph is validated against actual generated mesh lengths: no missing
vertices/indices, overlapping ranges, zero-length organ, invalid parent order,
or disconnected forced parent is admitted. This sidecar is optional and leaves
existing GLB bytes unchanged for identical presets. IDs are stable for an
identical preset/seed/software revision, **not** guaranteed across stages or
arbitrary topology edits. The next gate is explicit stable developmental organ
paths (plant→axis→phytomer→leaf/inflorescence) with birth/death semantics.

## Native CI dependency acquisition hold

The existing OpenAlea/Blender workflow pixel oracle is pinned to **Ubuntu's
Blender 4.0.2**. `tools/install_blender_apt.sh` is a fail-closed, Ubuntu
24.04-only acquisition candidate that skips Azure `apt-mirrors.txt`, keeps
Ubuntu repository signatures, tries two explicit upstream mirrors with bounded
update/download/install phases, and verifies Blender 4.0.2+NumPy+Xvfb before
allowing original raster/pixel checks. Offline syntax/negative controls are in
`tools/test_install_blender_apt.sh`.

This is a **corrective candidate, not a proven CI fix** until the original
native workflows complete successfully and original pixel baselines pass.
No reference-image or validator-threshold relaxation is authorized.
