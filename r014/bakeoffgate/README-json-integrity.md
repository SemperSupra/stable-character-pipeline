# R014/Q1 JSON admission correction (public synthetic)

This source-safe change is stacked on the R014/Q1 bakeoff gate, not merged into public main.

## Threat model and scope

Go's default `encoding/json` struct decoding accepts duplicate keys, including in nested objects and arrays. A source/venue gate must reject ambiguous input before interpreting any field or digest. Input size is bounded to 1 MiB to constrain parser work. The duplicate-key pass uses a JSON token stream and compares decoded names, including Unicode-escaped aliases.

## Qualification

- Positive: existing strictly encoded plan remains decodable.
- Negative: duplicate top-level venue, nested SHA, clip motion SHA, arm frames, Unicode-escaped duplicate name, and oversized payload all reject.
- Run: `cd r014/bakeoffgate && go test -race -count=1 -v ./... && go vet ./...`.
- Eligible: original Go/JSON synthetic fixtures only, public free-tier GitHub Actions on this PR.
- Not in scope: real MHR/CMU source, rights authentication, model quality, film acceptance, private Actions, canonical promotion or merge.

The gate remains diagnostic and retains every R014/R009 HOLD.