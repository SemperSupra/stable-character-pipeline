# One semantic scene, three audience projections — R036

This additive original synthetic interface workcell extends initial Go geometry contract PR #519. No dependencies or human subject/model/mesh data. The same `anatomy.Scene` stores source structure IDs, visibility and physics; HTML form and JSON HTTP clients operate it via `GET /api/describe`, `GET /api/scene`, and typed `POST /api/view`. See `../cmd/anatomyprobe` for the deterministic CLI use of the same schema. All surfaces distinguish rendered visibility from simulation physics.

For human usability, the browser gets a semantic HTML fieldset of native checkbox controls per anatomical system, search, per-structure textual view and label-language selection EN/DE/TH/Latin; visible status is announced with `role=status`. No inaccessible 3D canvas is required to understand the structure tree, but an actual 3D renderer has NOT been integrated or accepted. Full screen-reader (VoiceOver/NVDA), keyboard, touch, high-contrast and 200% zoom testing remain **NOT_RUN**, even if test source markup exists.

Agent and deterministic automation use the *same* typed JSON commands. Mutating operations require the schema, current revision, supported system, application/json and bounded body; failures use status/diagnostic code and do not change state. No universal engine/plugin/asset registration or paid model API, no derived claims of patient anatomy. Server defaults to 127.0.0.1, not intended as an Internet service.

In a disposable environment:

```sh
cd research/anatomy-bakeoff
GOTOOLCHAIN=local GOPROXY=off go test -race -count=1 ./...
GOTOOLCHAIN=local GOPROXY=off go vet ./...
GOTOOLCHAIN=local GOPROXY=off go run ./cmd/anatomyweb --listen 127.0.0.1:8777
```

`go test` runs `net/http/httptest` in-process with no network or browser installed. A fresh interactive browser must still be independently evaluated before accessibility/UX acceptance. All source and test receipts remain in DLE #175, child of #174; no merge/release/deploy.
