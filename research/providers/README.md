# Anonymous 3D / motion provider qualification (G5; research only)

**Owning authority:** [public MMD #19](https://github.com/SemperSupra/stable-character-pipeline/issues/19), source-neutral discovery feeding the **private product DLE #2** only after independent rights/source/admission. **Preregistration:** [#19 comment 6506988410](https://github.com/SemperSupra/stable-character-pipeline/issues/19#issuecomment-6506988410).

## Scope and execution

A single Go-stdlib metadata probe with exactly three public GitHub Actions matrix workers and **no credentials, media downloads, asset rehosting or scraping**. Each provider has exactly **one** statically allowlisted HTTPS request per run, max **128 KiB** of body inspected, **12 s** timeout, no redirects, no user cookies, no rate-limit retry, no sign-in, no anti-bot bypass. The sample SHA256 is a digest of the **bounded response sample**, not an asset or authoritative provider manifest. A green CI job means *the harness ran*; it does not mean any provider was admitted.

Run locally, if network access and permitted:
```sh
cd research/providers
go test -race -count=1 ./...
go vet ./...
go run . -batch A
go run . -batch B
go run . -batch C
```

| Batch | Providers | Test scope | Admission restriction |
|---|---|---|---|
| A / API native | Poly Haven, ambientCG, Openverse, Wikimedia Commons | 4 single bounded metadata endpoints | Licenses, credit, source owner, rate limits must be checked before acquisition |
| B / models and mocap | Khronos glTF samples, CMU mocap, Quaternius, Kenney, KayKit | 5 source/readme/license/page accessibility probes | A landing page is **not** a machine download API; CMU says **do not crawl**; QAL blocks standalone asset redistribution |
| C / conditional | Open3DLab RSS, given Open3DLab project, Sketchfab Data, BlenderKit, Poly Pizza, OpenGameArt | 6 single metadata endpoints | Anti-bot, 401/403, arbitrary HTML and undocumented API remain **HOLD**; Sketchfab model download requires OAuth |

## Machine receipts and invariant definitions

Each output JSONL line: `provider`, `lane`, `endpoint`, `rights_gate`, `http_status`, `content_type`, `body_bytes_sampled`, `sample_sha256`, `truncated`, `result`, `elapsed_ms`. Stored in per-lane workflow artifacts 14 days; results should be copied in summarized form back to the owner DLE with the exact run ID and head SHA. No HTTP response bodies, authorization headers, signed download links, local private paths or raw third-party media are persisted.

Results: `API_METADATA_OK` and `FEED_METADATA_OK` indicate only syntactic/transport eligibility, not source licensing, API SLA or file download rights. `TEXT_METADATA_OK` is first-party static documentation reachable. `HTML_ONLY_REVIEW` is public page accessibility, **not** API integration. `ACCESS_HOLD`, `CHALLENGE_HOLD`, `REDIRECT_HOLD`, `RATE_LIMIT_HOLD`, `CONTENT_MISMATCH_HOLD`, `TRUNCATED_REVIEW`, `TRANSPORT_HOLD` and other holds fail closed. A legitimate provider may return a temporary HOLD from a given runner region or IP; don't circumvent it.

No provider is **acquisition-qualified** in this first batch. No automatic collection loop, downloads, training, CPE promotion, private real-person/source ingress, merge, release, or deployment.

## Proposed adapter contract for next stage

Reuse a single versioned provider adapter consumed by all three audiences:
```text
provider_id / capability_version
source_asset_id / source_url / discovery_timestamp
metadata_snapshot_hash / metadata_timestamp / locale_tags
asset_kind (model|rig|motion|pose|material|audio|scene|reference)
formats / dependencies / units / axes / timebase / skeleton_descriptor
author / license_id / license_url / attribution / evidence
permissions {view, download, adapt, redistribute, commercial, training}
source_rights_verification (unknown|verified|denied)
asset_sha256 / file_size / archive_manifest / binary_mime
admission_state (discovered|metadata_qualified|rights_hold|download_admitted|quarantined|format_qualified|rejected)
toolchain_evidence {importer_version, native_format, conversion_loss, rerender_receipt}
```

**Gates:** discover → metadata/format schema → independently verify per-item rights → obtain actual permitted download link (if available) → explicit download admission → checksum and archive inspection in quarantine → toolchain import/retarget tests → independent scene/rig/motion QA → owner review for promotion. Never infer commercial/derivative/training/redistribution permissions from anonymous download access. Never put full rights-restricted asset files in the public repository or public artifacts.

**Three audiences:** human-readable provider cards and accessible exception explanations; CLI JSONL and explicit permissioned fetch; typed agent capability discovery and denied/unknown controls. All frontends share the same provenance, rights state and immutable evidence records. Go adapter orchestration; Blender/MMD/FBX/glTF specific backends remain replaceable.

**Sequential dependencies:** transport result → provider policy/rights assessment → download admission → assets and file hashes → importer capability/rig proof. Batches A/B/C and their controls are independent and may run in parallel; private R009 must stay blocked until its own admission and source custody.

### Reference policies

- [Poly Haven API](https://polyhaven.com/our-api): API use is public but UI must credit provider.
- [CMU FAQ](https://mocap.cs.cmu.edu/faqs.php): request published archives rather than crawling.
- [Quaternius QAL](https://quaternius.com/license.html): restrictions on redistributing standalone files.
- [Sketchfab Download API](https://sketchfab.com/developers/download-api): OAuth required.
- [Wikimedia API rate limits](https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits): identify clients and respect 429.
- [Openverse API](https://api.openverse.org/v1/): anonymous queries subject to limits.
