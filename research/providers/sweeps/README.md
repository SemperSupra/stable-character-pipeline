# Responsible multilingual asset discovery and CPE feedback (research-only)

Owner authority: [Stable Character MMD DLE #19](https://github.com/SemperSupra/stable-character-pipeline/issues/19) [preregistration 6507659227](https://github.com/SemperSupra/stable-character-pipeline/issues/19#issuecomment-6507659227). Stacked public source-clean workcell after gated providers PR #117. None of this is an accepted CPE ontology or an implementation of the existing private CPE query compiler.

## Composition, not another semantic authority

- **Known concept:** existing private CPE Concept Authority -> existing private `SearchPlan` -> `concept-search-adapters-private@feat/mvp-bootstrap:src/content_search_adapters/searxng.py` known-concept `lower_dry_run` -> *approved, separately scoped query variants* -> provider-specific search or opt-in self-hosted SearXNG JSON engine. Public testing uses only **original synthetic forms** and opaque fixture concept/projection refs, not real protected plans.
- **Unfamiliar intent:** existing CPE #241 frontier discovery using independent lexical resources, source taxonomy and native-language sources -> bounded candidate forms and later CPE #202 Stage-P `ConceptDiscoveryProposal`. The public `PlanSynthetic` accepts this fixture packet; it does not create definitions/translations or promote candidates.
- **Language coverage:** fixture EN, DE and TH, extensible to source-native JA/ZH and others only from proven lexical form evidence; preserve BCP47-like lowercased tags and source-native spellings; `hard_negative` and `no_equivalent` are never positive search expansions. Terms with merely similar spelling are not exact concept mappings. No silent English-pivot assumption.
- **Retrieval:** provider-native APIs prioritized, independently verified hosted SearXNG engines second, no uncontrolled shared public SearXNG instances or open relay. Source `ProviderID`, `SourceLineage`, response and country/language coverage preserved. Search result ranking is **not** conceptual truth, concept absence, download rights, or independent source confirmation.
- **Feedback:** `scp.concept_discovery_proposal_candidate.v1` is an intermediate compatible RESEARCH-ONLY evidence envelope for owner CPE #202 intake, not an independent accepted schema. It dedupes per source ancestry, maps `lexical_gap` to lexicalization proposal, `collision` to hard negative, `unmapped` to unknown residual. `canonical_concept_id` stays null and `policy_mutation=false`. No automatic writes to private authority.
- **Research design:** protect CPE #229 independent reference vs treatment separation. Source-only public synthetic reps are `CONTAMINATED_REHEARSAL` for any later independent benchmark. Do not claim improved multilingual concept recall from these fixture passes. Compare query cost / new validated mappings / precision / false novelty after an independently admitted real rep per CPE #311.

## Citizen rules — machine-observable holds

1. **Check provider permission before traffic:** distinguish documented API from HTML crawling; independently approve the appropriate terms, account scope, rights and intended operation. A permissive robots file is **not** a waiver of terms. Crawlers must follow RFC 9309, and robot fetch failures must not be treated as permission.
2. **Identify ourselves:** descriptive user-agent and contact link, provider-specific required attribution in the human UI. Poly Haven live API requires an identifying user-agent or referrer and visible origin credit.
3. **Avoid unnecessary traffic:** prefer provider API / feed and local cached metadata; dedup equivalent terms, retain language/source provenance; default research maximum is 1 concurrent request/provider, at least 1.5 seconds between requests, max 30 requests/minute, max 200/day, max 3 pages, max 128 KiB/read (these are **hard upper bounds**, not promises that any provider permits that rate); each target has a **lower** individually qualified budget if required.
4. **Respect refusal:** 401/403, CAPTCHA/Anubis, blocked format, TLS failure, robots disallow, missing terms, 429 without Retry-After, or provider policy unknown => HOLD, not retry with rotating account/IP/proxy. Honor Retry-After and ceilings for 429/503, no aggressive backoff loops.
5. **Crawl restraint:** SearXNG can impose upstream search load. Only self-owned/admitted instances with JSON enabled (often disabled on public instances) and source-engine caps; avoid over-fanning queries. No mining protected public endpoints via shared SearXNG in the current workcell.
6. **Rights and contributor fairness:** asset-specific view/download/use/derivative/publishing/training permissions are separate facts. No uploads or hosted releases without explicit owner action and exact rights proof. Respect provider attribution and creator restrictions even when file URLs work.
7. **Observable execution:** human UI: source labels, permissions and reason for HOLD; automation: immutable JSONL receipts/CLI; agents: discoverable typed capability and dry-run plan. One common policy and evidence state, accessible and inspectable.

**Actual code limits:** `sweeps/politeness.go` is an **offline gate simulator**: synthetic booleans are NOT signatures, downloaded live policies, token buckets shared between workers, global distributed quotas or live robots parsing. Actual production must use a durable per-origin global quota ledger, verified policy snapshots/signatures, trusted credential broker, cache, cancellation, and independent review before physical traffic.

## Reproduction

```bash
cd research/providers
go test -race -count=1 ./sweeps ./cmd/multilingual-demo
go vet ./sweeps ./cmd/multilingual-demo
go run ./cmd/multilingual-demo -lane plan
go run ./cmd/multilingual-demo -lane citizen
go run ./cmd/multilingual-demo -lane cpe
```

Native public GitHub Actions workflow `provider-multilingual-safety.yml` launches 3 independent $0 standard CPU jobs and retains 14-day JSON results. Public CI conducts **zero external provider traffic** in this workcell.

## Next integration admission

1. Bind to exact *private* CPE source-owned projection and search adapter after authorizing a sanitized query packet and verifying no private semantic leakage; preserve independent blinded comparison.
2. Add provider policy evidence including actual site rules, robots results (when appropriate), quota & scope, per-source terms, cache and user-agent requirements in a *trusted* broker. No distributed traffic without a global per-host quota.
3. Test one specifically rights-cleared public asset download from a documented API, hash/quarantine it and qualify Blender/MMD import under a separate owner-authorized workcell, not via this sweep test.
4. Independently validate proposed CPE lexicalizations with cross-language source evidence and hard negatives before owner-controlled accepted snapshot update; rerun affected consumers with regression evidence.

References:
- [RFC 9309 Robots Exclusion Protocol](https://www.rfc-editor.org/rfc/rfc9309.html)
- [Wikimedia API rate limits (2026)](https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits)
- [SearXNG Search API](https://docs.searxng.org/dev/search_api.html) and [limiter](https://docs.searxng.org/admin/searx.limiter)
- [Poly Haven API terms](https://github.com/Poly-Haven/Public-API/blob/master/ToS.md)
- [CPE #202](https://github.com/mark-e-deyoung/concept-policy-engine-private/issues/202), [#241](https://github.com/mark-e-deyoung/concept-policy-engine-private/issues/241), [#229](https://github.com/mark-e-deyoung/concept-policy-engine-private/issues/229), [#311](https://github.com/mark-e-deyoung/concept-policy-engine-private/issues/311)
