# R4 direct STOP / storage independence test double

**Bounded, device-free synthetic test** under Audio Foundry #9. This is NOT a production host, acoustic safety system or deployed device supervisor. It exists because [SQLite fault PR #747](https://github.com/SemperSupra/stable-character-pipeline/pull/747) showed a stopped command can fail to commit when the database is unavailable.

`StopDirect` changes a single atomic, session-local render-permit state without calling a database, filesystem, HTTP, Go channel, timer or general scheduler. The test uses a blocked *independent* storage worker, concurrently attempts host START vs STOP, proves no **subsequent** simulated render call returns nonzero after STOP returns, and distinguishes requested `StopPending` from separately observed `StopObserved`. The callback mock performs one atomic load and no blocking operation.

**Not yet solved:** in-flight callback frames that read the permit before Stop, buffers already queued to OS/device, independent real hardware silencing, headphone route changes, user gesture/OS authorization, service/process death, crashed host supervisor, physical SLA, calibrated SPL and verified actual audio cessation. The simulated host START/STOP observations are not authenticated. A real host STOP path must preempt output directly at its device driver/backend, independently of journal persistence; the state here cannot accomplish that. No automatic sound, network, real recording, merge or release.

Reproduce `cd audio-control/control && go test -race -count=1 ./directstop && go vet ./directstop` (public 3-OS CPU runners).
