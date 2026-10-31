# Independent RC0 ↔ R7 decoded-frame differential (original-only)

This additive public research tool compares independently archived original H264 outputs from the SAME original source without treating ground truth, annotations, or detector boxes as a scientific human-motion oracle. Input is four local ZIPs: original native media plus original compact evidence for baseline and candidate. Before decoding it verifies ZIP CRC, source/rights hash, native GLB and editable blend SHA, both required H264 source SHA, retained historical fullbody FAIL and draft release nonpromotion. It never reads confidential person media in public GHA.

Run with: python3 qualification/release_crossrun/compare.py --base-media BASE.zip --base-evidence BASE-EVIDENCE.zip --new-media CANDIDATE.zip --new-evidence CANDIDATE-EVIDENCE.zip --out RESULT.json

All measurements are observed decoded RGB24 equality, per-frame and overall mean absolute difference, maximum channel delta and PSNR. There is deliberately NO normative pixel difference threshold, no claimed human gait pass, and no private R009 product admission. Real-source identity rights, joint/skin/contact, behavior and release approvals remain independent held gates.

## Verified earlier independent original-only RC0-versus-R7 observation, 2026-10-31

Original source SHA256 c1ebf84b60bacaf4d1132f88dcfd588c9b94fa1790a3e48f163dfd195e22b449; native six-bone GLB SHA256 1d6271f2a22a83a8ee1376d73b6087a4fe0b9f4bcc7ba246a4d569a2f7bf419d. Both match between RC0 #208 GHA 41214144577 and OCI R7 #210 GHA 41216265742.

Front H264 baseline SHA 8da6f11403972d772af36a2b2a76435994f7699839bab43839cd1cfaad12af84 vs candidate edcb3fb1ebec9ff9d381681559e8398baf438ca19214110e2ad47a8284d97aeb: 24/24 decoded RGB frames pixel identical even though container bytes differ.

Oblique H264 baseline SHA 41987748db651e1aa4b26563064fc1a72225cff815b7dd167e776b4d58366678 vs candidate 68a8d1147bc98f38d883f201fcfc7a0bc2e6afe2550c1744a9edffed43034672: 22/24 frames pixel identical; only frames 21 and 22 differ. Frame21: 188 channel bytes change, max delta 5/255, mean channel difference 0.00044849537037037037. Frame22: 6 channel bytes change, max delta 1/255, mean 0.000008680555555555556. All-frames overall mean absolute RGB difference 0.000019048996913580246 and PSNR 92.147 dB. All four original videos have 24 frames, 12/1 fps, 640x360 resolution.

This comparison is reproducible and makes no claim of MP4 byte equality or accepted source-human motion. The original full-body synthetic proxy remains FAIL_ABSTRACT_LIMBS_ONLY, protected R009 NOT_RUN_NOT_ADMITTED. Public CI runs new fictitious black/white original-only FFmpeg test videos; real original RC0/R7 binary archives remain privately custodied in owner-only Drive and no Drive identifiers or protected source are to be published in public Git.

Test: python3 -m unittest discover -s qualification/release_crossrun -p 'test_*.py' -v
