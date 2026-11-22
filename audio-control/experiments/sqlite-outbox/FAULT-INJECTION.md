# SQLite WAL / control-plane failure injection (R2-SF)

This is an **independent red-team child of the synthetic SQLite outbox [PR #743](https://github.com/SemperSupra/stable-character-pipeline/pull/743)**. It owns only `test_faults.py` and this note; the original SQLite candidate implementation and actor-owned #738–#740 remain untouched.

The three additional synthetic CPU tests exercise:
- **Outbox INSERT abort after operation/session writes**: SQLite `BEGIN IMMEDIATE` must roll back *all* records, so a partly admitted START is not represented as accepted.
- **STOP outbox insert failure after canceling pending START**: the entire transaction rolls back. The prior START remains pending, so `requires_host_reconcile=true` and `may_issue_start=false`; **this is a demonstrated emergency STOP failure condition, not safe STOP behavior**.
- **SQLite RESERVED write lock contention:** a second writer's STOP admission fails without silently updating a session or outbox row. The OS host must have an independent privileged shutdown/STOP path that does **not depend on a successful SQLite commit**.

These tests are stronger than a mere normal-case `WAL`/dedupe interview but **not** a power-loss, filesystem-corruption, disk-full, mTLS, signed host event, or actual acoustic validation. They deliberately use SQLite `RAISE(ABORT)` triggers and a 50 ms contention window, not production fault-injection services. Original research uses a caller-supplied fake human grant: no real OS/user security is present.

Run `cd audio-control/experiments/sqlite-outbox && python -m unittest discover -p 'test_*.py' -v`; inherited dedicated 3-OS public free-tier workflow must run every new test with no skips. Do not treat a green result as authorization for human headphones; keep actual device admission HOLD.
