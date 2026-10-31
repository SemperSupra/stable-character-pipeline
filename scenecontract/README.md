# Three-audience scene-contract conformance reference (draft)

Original **source-safe structural** `scp.scene.v1` only. This is **NOT** R009 real-character app integration, rendering, human-motion qualification, private rights admission or authorization to merge/release. The two actors in the public sample are self-authored fictional identifiers and full digests are placeholders, not asset content.

- **Human:** accessible keyboard HTML form on `http://127.0.0.1:8765/`.
- **Automation:** `cd scenecontract && go run ./cmd/scenecontract validate sample.synthetic.json` (JSON decision / exit 0 only for structural PASS); local HTTP `POST /v1/scenes/validate` and `application/json`.
- **Agent:** `GET /v1/capabilities` machine-readable endpoint discovery pointing to the **same** structural preflight validator.

Start loopback reference: `cd scenecontract && go run ./cmd/scenecontract serve`. No deployment container, execution queue, source importer, job scheduler, renderer or identity claim is included. Private product must integrate the actual R009 application behind this schema after reviewer and owner gates. The structural PASS **cannot** be used to promote real R009 or overwrite scientific FAIL/UNKNOWN. The server has no authentication and binds **only** 127.0.0.1; do not expose through a public reverse proxy or rely on it for production operations.

Go stdlib only, max 1MiB JSON, unknown/duplicate/trailing JSON rejection, origin and media-type fail-closed for API, input validation for IDs, SHA, source classification, actor and camera uniqueness; tests assert CLI/HTTP parity and negative controls. See public release #1 and private root #23.
