# Original reusable characters — R009 nonrestricted candidate

Two newly created fictional characters (`AsterOriginal`, `JuniperOriginal`) are authored as programmatic glTF 2.0 skinned geometry with 17 joints/person, full-body material groups, individual hair/face/accessories, and a 72-frame authored six-second approach. **No third-party character meshes, performer identities or animation clips were used.** This is a free-to-reuse owner-controlled original synthetic research fixture; public licensing is an explicit owner publication decision, not silently declared here.

Run without external packages:

```sh
python3 -m unittest -v test_original_glb
python3 generate_original_glb.py --out original.glb --receipt generated.json
python3 verify_original_glb.py --input original.glb --receipt verified.json
```

The independently implemented witness verifies two live glTF skins, 17 joints each, weighted multi-joint mesh deformation bindings, 72-frame animation tracks, separate approaching roots, source class, malicious false human-acceptance claims, and format integrity. A successful check is **technical, not scientific or aesthetic acceptance**.

The associated public-only workflow downloads SHA-checked Blender 4.5.15 and invokes `render_blender.py` on standard $0 public CPU runner. The worker creates an editable `.blend`, a two-camera 72-frame 640×360 H.264 preview, and a source-bound native receipt. Animation is intentionally simple; plantar contact, foot-skate, JCS/ROM, self-collisions, facial fidelity, realistic clothing physics, and independent human L1/L2/VLM quality are **UNKNOWN or NOT_RUN** until actual rendered evidence is examined.

## Rights-source options for higher-fidelity next passes

1. Quaternius [Universal Base Characters](https://quaternius.com/packs/universalbasecharacters.html): official CC0 standard rigs, 6 body bases and hairstyles; pin exact downloaded archive bytes and current public license page; commercial/derivative rights allowed subject to asset-specific constraints.
2. Quaternius [Universal Animation Library](https://quaternius.itch.io/universal-animation-library): CC0 standard root-motion clips; do not assume paid source .blend edition is available at $0.
3. MakeHuman/MPFB **core graphical assets** CC0; engine/software GPL/AGPL remains separate. Clone/use core media only after identifying exact file-level licenses.
4. Microsoft Rocketbox MIT-licensed assets; preserve MIT license and upstream notice. Not automatically photoreal or identity-authorized.

Keep original Naomi and Alison artifacts privately quarantined/segregated; their original identity-specific and vendor source/rights gate is not used as acceptance evidence for this self-authored product track. Do not alter closed R009 initial first failures, falsely relabel prior source footage, commit vendor data or grant merge/release/CPE/product acceptance.

## Audiences

Human: inspect editable Blender and two video views plus source/license card.
Automation: generate/verify CLI with JSON receipts and exit codes.
Agent: same schema and source-bound receipt; no implicit ability to perform privileged source acquisition or release.

## DOPAV

Discover provenance → Observe frozen source → Plan independent generated assets → Apply isolated generation and native render → Verify glTF, native bpy, ffprobe, multiple views, independent visual/ROM/sole falsifiers. Preserve first failures. Large media in approved Drive custody after whole-byte readback; small source/tests/receipts in Git/DLE.
