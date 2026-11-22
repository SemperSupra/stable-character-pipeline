# Audio Control R0 — host authority and command ingress

Experimental contract-only workcell N2, stacked on [protocol PR #726](https://github.com/SemperSupra/stable-character-pipeline/pull/726). These synthetic JSON cases do not authenticate devices, users, agents, speech, microphones or servers.

A syntactically valid `host_started` is NOT proof that physical output started. `audio_control.r0` JSON Schema describes two **shapes** of messages; it cannot know which endpoint/transport supplied them. There must be two separate host-enforced channels:

- `untrusted_submit`: human, accessible UI, agent, script; accepts `configure/request_start/stop/close`. The host **derives** `principal_id`, device/lease/epoch from authenticated local OS and selected user context. Do not trust client-supplied principal, host privilege, target identifier, or operation digest unconditionally. A request-start alone does not perform playback or bypass confirmation.
- `verified_local_host`: adapter-origin, immutable authenticated/matched device and session/epoch; accepts only `host_started/host_stopped/host_completed/host_failed`. No remote client route or agent tool is allowed to submit these observations; a local host signature/identity/lease check and actual device event are required for admission.

The `ingress-r0.json` corpus declares seven **schema-valid** examples that are either permitted or forbidden *according to transport context*. `check_vectors.py` asserts that classification, using the same external JSON Schema validator as parent #726. It does not implement OS host authentication. Only a future verified adapter can turn these examples into real authorization checks.

**Release HOLD:** verified origin, canonical principal overwrite, event ordering, device identity/lease consistency, per-capability physical permissions, audio exposure policy, interrupted/unknown host STOP, durable replay/outbox, macOS/Windows/Android/Linux hardware integration and private media retention. No new HTTP server or general broker is authorized here.
