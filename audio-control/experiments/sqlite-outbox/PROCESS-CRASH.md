# Audio Control R3 — SQLite WAL abrupt-process-exit falsifiers

This is a **test-only disjoint child of SQLite fault workcell [#747](https://github.com/SemperSupra/stable-character-pipeline/pull/747)**. It adds only `test_process_crash.py` and this document; no modification to the SQLite candidate implementation or the local actor's file-journal process tests [#740](https://github.com/SemperSupra/stable-character-pipeline/pull/740).

Three real Python subprocess tests call `os._exit(91/92)` deliberately:
- **Uncommitted process death** after opening a SQLite `BEGIN IMMEDIATE` transaction and writing candidate session/operation rows, but before creating an outbox item: on next process startup SQLite recovery must expose zero operations/outbox/sessions and pass `PRAGMA integrity_check`.
- **Committed process death before reply delivery**: original START intent+outbox are present, yet no physical playback is assumed. New process returns historical replay receipt without issuing a second START effect; the host must reconcile actual device state separately.
- **Interrupted effect recovery then STOP**: STOP transaction cancels the pending start intent and commits a host-stop request, but `requires_host_reconcile` remains true. An outbox row and a green SQLite integrity check do **not** prove that sound stopped.

These are **process-exit**, not simulated mains power loss, full disk, controller PID theft, multi-host ordering, hardware signal verification or SQLite file corruption tests. STOP while storage is unavailable remains blocked as shown by sibling #747: the owning OS-host audio supervisor must have a direct privileged device-stop fallback independent of DB. Original acceptance is governed by Audio Foundry [#9](https://github.com/SemperSupra/stable-character-pipeline/issues/9) and root AGENTS.

The inherited public 3-OS `audio-control-r2-sqlite-outbox.yml` must execute the original eight tests, three fault-injection tests and these three new ones. All fixtures are synthetic; no real acoustic output or private data; no production integration/merge/release.
