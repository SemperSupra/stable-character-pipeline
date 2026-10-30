# Artifact routing contract — source-neutral public projection

Status: research policy candidate; no merge, deploy, release or owner acceptance implied.

Every generated artifact MUST receive a deterministic placement decision with its producer and observer receipts; GitHub Actions artifacts are **temporary transfer evidence**, never durable binary retention.

| Placement | Route | Examples |
|---|---|---|
| `GIT_TEXT` | Source-controlled text only | Build recipes, code, tests, schemas, sanitized small manifests |
| `GIT_DLE_RECEIPT` | Owning issue/DLE or small receipt tracked in Git | SHA-256, native and independent CI, rights/provenance, first failure, decisions/next baton |
| `PRIVATE_BYTE_STORE` | Authorized private binary storage, NOT Git history or public CI | Rendered video/audio, full native PCM, rigs, 3D meshes, textures, media bundles, model weights, large archives |
| `PRIVATE_QUARANTINE` | Restricted review storage | Unknown or unadmitted licenses/rights/provenance; never use as a validated source |
| `EPHEMERAL_RECOMPUTABLE` | Temporary runner/workspace with explicit disposition | Pure caches/intermediates whose deterministic builder is durably recorded |
| `HOLD_NO_PUBLICATION` | No public transfer | Missing rights or independently verifiable hash, private source risk, unavailable authenticated byte custodian |

**Threshold principle:** placement depends on *role and sensitivity*, not a binary size cutoff. Even small MP4 previews are media, not source text. A private byte object plus a signed-off source-controlled descriptor are one logical artifact, not duplicate authority.

## Required artifact descriptor (safe projection only)

```json
{
  "schema": "stable_character.artifact_routing.v1",
  "artifact_id": "sha256:<64 lowercase hexadecimal digits>",
  "media_kind": "original_synthetic_media",
  "placement_decision": "PRIVATE_BYTE_STORE",
  "content_sha256": "<64 lowercase hexadecimal digits>",
  "size_bytes": 0,
  "source_rights": "ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC",
  "producer_revision": "<public source commit>",
  "native_receipt_id": "<CI run or independent digest>",
  "observer_receipt_id": "<independent CI run or digest>",
  "lineage_parent_sha256": [],
  "status": "CLASSIFIED",
  "retention": "retain_until_explicit_review",
  "limitations": ["research_only", "not_released"]
}
```

The example above illustrates field meaning and is **not** an accepted manifest or proof that an upload occurred. Public receipts MUST OMIT all private file/folder IDs, signed download URLs, access tokens, identity, private network details, actual internal machine/hardware/model inventory, and private provenance or correlated operational fingerprints. Only synthetic, permitted source-clean fixtures belong in public build workflows.

## Custody and reproducibility invariants

1. Compute exact original byte count and SHA-256 before transfer, admit rights before external processing, and preserve the immutable source digest and producer revision.
2. For substantial binaries the authorized trusted executor uses a resumable, bounded direct-to-private-store transfer with idempotent content-addressed placement; do not use the public control plane or Actions runner to hold private credentials.
3. Verify the uploaded complete object through an independent authenticated download and full SHA-256 comparison. Provider upload response or file size alone is not a verified retention receipt.
4. `GENERATED → CLASSIFIED → RIGHTS_CHECKED → HASHED → STORED → REHYDRATED_VERIFIED → REGISTERED`; separate owner-controlled promotion to ADMITTED or RELEASED. On mismatch/missing rights, HOLD or QUARANTINE; never silently change the declared hash.
5. Results, artifacts, content identities, and first-failure evidence are discoverable and actionable by humans, automation CLI, and agents. Tooling should expose plain structured status and localization hooks (English, German, Thai), never inert controls.
6. Before retiring temporary runner artifacts, ensure durable code/recipe + numerical evidence in Git/DLE and complete verified reusable media in authorized private byte storage. Explicitly designate throwaway items as `EPHEMERAL_RECOMPUTABLE` and record the choice.

This public document is a **sanitized projection** of private owner-controlled artifact-custody policy. It contains neither a private cloud locator nor an invitation to retrieve restricted media. No private infrastructure configuration or credentials are needed to validate the public schema.
