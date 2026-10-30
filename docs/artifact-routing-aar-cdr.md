# Artifact destination and evidence custody — Stable Character Pipeline

> Source-neutral public contract. Governing workset: [public G5 DLE #19](https://github.com/SemperSupra/stable-character-pipeline/issues/19); actual private object location and provenance: separate **private** Stable Character DLE. Inherits the established AAR/CDR architecture, **not** a new storage/upload subsystem.

## Rule

Git/DLE owns **authority**: source code, docs, versioned config, provenance, rights, immutable SHA-256 descriptors, asset graph, source-ref and workflow hashes, acceptance decisions, state transitions, validation tests, and next executable baton.

Private Google Drive owns **bytes**: reference media, images, audio, videos, downloaded 3D assets, clips/datasets, model weights, large logs, `.blend`, `.glb`, `.fbx`, `.pmx`, `.vmd`, H.264 previews, screenshots, checkpoint artifacts, ZIP archives and intermediate renders, subject to explicit rights and user-specific custody. Drive is **not** semantic, rights, release or DLE authority. GitHub Actions artifacts are expiring **transit staging**, not durable preservation.

### Route every created artifact before running

| Kind | Git authority | Byte placement | Acceptance |
|---|---|---|---|
| Source, build/test code, synthetic configs/docs, safe small JSON schema | Public Git if sanitized; otherwise private Git | No Drive copy needed unless approved independently | Tests and source review |
| Small provenance/rights/QA/DLE receipts | Sanitized public Git when safe; sensitive full receipt private Git | Optional human-friendly Drive copy; not authority | Source and SHA independently matched |
| Large structured manifests/logs/observability traces | Small private Git descriptor and DLE, synthetic summary public if safe | Private Drive receipts cache | Verified SHA and privacy boundary |
| Source 3D models, motion clips, photographs, footage, textures, sound, weights | Private Git content-addressed source index; public only source-neutral permitted references | Private Drive shared originals or subject-specific originals; missing rights → quarantine | Source author/license, permitted operations, full SHA + rehydration |
| Editable derivatives and interchange exports | Small private Git lineage and QA receipt | Private Drive derivatives/working assets | Input lineage, transform provenance, remote rehydration |
| MP4 playback, contact sheets, iPhone previews | Private manifest (sanitized examples may be public) | Drive derivatives with accessible playback copy; source stays editable | Human review and media probe |
| Restricted vendor assets or real-person subjects | Private Git DLE only; do not publish IDs, source URLs with account tokens or protected context | Restricted private Drive subject originals or quarantine | Explicit source license, privacy and source-custody approvals |
| Temporary builds/cache, ephemeral lock state | No permanent Git | Local scratch (delete at expiry) | Irrelevant disposable bytes |
| Secrets, OAuth refresh tokens, private key files, `.local/auth` | **Never Git** | **Never Drive** | Trusted secret broker only |

The byte destination depends on the **artifact class and custody**, not simply its size. A 6KB GLB is still a binary artifact; a 2KB private subject descriptor still belongs in private Git. No unreviewed media in public Git or public Actions.

## AAR/CDR transport, not a competing implementation

1. **Discover/Observe:** inspect existing private manifest, Drive IDs, exact source, author, rights, object version, content-addressed identity. Dedup by SHA-256 and provenance, not filename.
2. **Plan:** emit `scp.artifact_route.v1` input and `scp.artifact_route_decision.v1`. Require state, license, sensitivity, file size, source SHA, destination class, expected exact Drive folder ID stored only in private configuration. An unverified field results in HOLD.
3. **Apply** within separately admitted actor:
   - Small objects: connector-native GitHub Actions `download_workflow_artifact` file reference to private Drive `upload_file` if the transfer is supported and its exact folder verified.
   - Large objects, rejected connector sizes, or streaming: **reuse the AAR/CDR user-authorized Drive API resumable upload/download** with bounded chunks, SHA256, no token in public CI; deterministic approximately 90 MiB part fallback when constrained, per-part+whole checksums and collision prevention. Never weaken AAR's original APK-corpus destination guard; use an independently verified destination profile.
   - Preserve all original content and licensed source restrictions; do not silently convert or upload unauthorized source media.
4. **Verify:** successful upload returns a real Drive ID and size. Independently read the bytes back from Drive, compute SHA256, inspect archive or media, compare original and remote. **Only then** transition to `DRIVE_REHYDRATED_SHA256_VERIFIED`. Record negative outcomes and first failures.
5. **Record in private Git/DLE:** source run/commit/artifact ID/expiry, canonical Drive ID, folder class (actual ID private), hash, size, creator/license, permitted operations, derivative lineage, verification receipt, and next recovery baton. A GitHub Actions green check alone must never set `admitted` or `Drive-stored`.
6. **Retain:** keep Actions packages until Drive readback and receipt persistence, within expiry. Preserve necessary original and derivative bytes in Drive; redundant unneeded scratch removed. Do not delete or overwrite a Drive object with conflicting SHA, or broaden sharing.

### Lifecycle
`DISCOVERED → RIGHTS_REVIEWED → HASH_VERIFIED → DRIVE_STORED → DRIVE_REHYDRATED_SHA256_VERIFIED → ADMITTED`

Each edge needs independent evidence. Rights unknown, API restriction, private-source disclosure risk, expired GHA artifacts, unresolved hash or missing Drive rehydration means **HOLD** at that edge. `ADMITTED` also needs an independent product/use-case owner decision; a byte-perfect ZIP does **not** imply render, rig, CPE or training approval.

### Three-audience contract

Human: browse the existing private Google Drive folder taxonomy, inspect accessible previews and clear per-object status/rights, and open owner DLE for reasoning.

Automation: stable JSON receipt & CLI read-only planner; policy-checked source fetch, resumable upload and full rehydrate; exact exit/error outcomes.

Agents: discover placement capabilities and request bounded store or verify operations only after runtime authorization; never infer credentials, source rights or acceptance from a model-generated flag. All share the same private content identity.

### Required route record

`schema, artifact_id, kind, sensitivity, rights_state, bytes, sha256, origin_ref, source_version_ref, producer_run_ref, logical_destination, actual_drive_id (private only), remote_rehydrated_sha256, observed_state, authority_dle_ref, next_baton`. Public fixture records use synthetic IDs and **never** real private Drive IDs, folder IDs, people, machines or auth endpoints.

**Technical caveat:** The public Go classifier in this PR determines *intended placement* only; it does not upload, delete, read private configuration or grant access. Production AAR/CDR transfers are a separately approved trusted executor.
