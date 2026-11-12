# R014 public native qualification (synthetic fixture only)

This isolated branch tests infrastructure for the private R014 human-asset research issue. It contains no R001/R002 files, faces, personal likeness, scanned source, pretrained weights, or protected data. All tests operate on synthetic geometry built inside disposable public GitHub Actions runners.

**Evidence boundary:** PASS means only that generic GLB, Blender save/reopen, skin and morph plumbing works. It does not mean realistic human bodies, facial animation, contact, physical soft tissue, or video have passed.

The branch is review-only. It must not be merged or used as a production asset without independent approval and DLE reconciliation.

Run the local zero-dependency control: `python3 -m unittest discover -v -s r014/tests`.
The workflow downloads the official Blender 4.5.16 portable release in the runner's temporary directory, verifies its publisher SHA-256 checksum, creates a simple two-bone skinned cylinder with one morph, reopens the .blend in a fresh process, tests evaluation, exports GLB, and checks the contract. All outputs are short-retention receipts.
