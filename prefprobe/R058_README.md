# R058: pair-specific evidence minimum and unambiguous scope identity

Private owner-intent authority: [R016 DLE #145](https://github.com/SemperSupra/stable-character-pipeline-private/issues/145). Experiment orchestration authority: [R037 DLE #176](https://github.com/SemperSupra/stable-character-pipeline-private/issues/176).

This *public research-only* Go workcell operates **exclusively on invented synthetic feedback**, never authentic owner choices or protected portraits. It is stacked on R046 [PR #558](https://github.com/SemperSupra/stable-character-pipeline/pull/558). It has no database, acceptance endpoint, canonicalization API, network client or private source.

## Why another control was necessary

R046 counted at least 5 votes per **shot/source/character scope**, not per compared A/B pair. Four votes for unrelated candidate IDs and one vote for the target pair could return a score for the target, despite only one target vote. This is an attribution/control defect, not an attack on a real user. R058 adds `PairVotes` keyed by the full typed, sorted candidate pair plus four scope dimensions, and requires five independent *exact-pair* votes before returning `SYNTHETIC_RANK_ONLY`. Reversing blinded A/B positions does not alter pair identity. Replay IDs are still globally idempotent; tie/neither/unsure count as abstentions only.

The previous delimiter-concatenated internal scope key allowed aliasing when shot and character IDs contained `/character/`. R058 uses a canonical JSON tuple to avoid cross-scope aggregation. Negative cases deliberately construct such an alias and demand abstention.

## Reproduce on public free-tier only

```
cd prefprobe
go vet ./...
go test -race -count=1 -v ./...
go run . -synthetic
```

Dedicated `.github/workflows/r058-pair-evidence.yml` runs the above in disposable public standard Ubuntu and emits only synthetic test logs, synthetic rank report and SHA manifest. Nothing from actual private R016 feedback or protected model assets may be admitted here.

**Qualified claim:** source-bound synthetic pair/scope evidence isolation and abstention correctness, **not** actual preference prediction, confidence calibration, photo-quality, user intent or accepted character selection. No real data adapter is enabled; P0 #167 remains gate for source-correct actual render candidate lineage, and the R032 gallery is the existing review entrypoint.
