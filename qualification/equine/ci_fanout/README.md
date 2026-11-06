# Fail-closed CI fanout reduction — original-synthetic PR #331 only

Why: GitHub evaluates `pull_request.paths` over a cumulative three-dot PR diff. Narrow workcell paths do not prevent eight old native workflows being relaunched by each new, unrelated child commit.

Solution: keep all original `pull_request` workflow/check names and scopes; add a cheap **within-job** proof gate before native steps. The gate asks authoritative GitHub Actions REST for a **completed/successful, fully native** older run on the same exact source/PR/base branch, requires ALL expected matrix jobs to have completed successfully and ALL correctly named artifacts to be unexpired, nonempty, and provider-reported `sha256:` digests. Full git ancestry and changed-path comparison must prove every intervening change is in a disjoint workcell; changes to the gate itself, current workflow, its input directories or an unknown path force a new native run. Any provider/token/cache/network/rate-limit/evidence failure forces native. No third-party action and no stored credential.

Every workflow still triggers on PR synchronize and reports status on the latest PR head. Unlike naive path-filtering or skipped-workflow approaches, there is **no skipped required workflow**; the native job either replays the existing source-matched technical proof or performs the full native steps. The selector is deliberately limited to the original-synthetic public branch and fixed immutable parent. The first rollout changes the workflow code and gate, so it necessarily re-runs all eight native qualifications once. A later single-workcell commit should reuse seven unchanged proofs while rerunning its owning workcell. This is not a persistent CI cache/service; artifacts remain subject to their seven-day retention.

Evidence reuse does not transfer scientific animal anatomy, sound authenticity, force-bearing contact, rights, CPE, merging or release authority. Independent source/CI holds remain. If the workflow topology, upstream parent, dependency manifest, runtime, ref or source classification changes, requalify; when in doubt rerun. The current explicit workcell dependency policy is conservative and fail-closed. Per-job checkout still consumes short runner startup, but expensive Blender/FFmpeg/test steps can be avoided.

Local adversarial controls: `python3 -m unittest discover -s qualification/equine/ci_fanout -p 'test_*.py' -v`; `python3 -m py_compile qualification/equine/ci_fanout/proof_gate.py`. The gate only calls GET (GitHub Actions REST), never changes GitHub state. Its own output says `run_native=true/false` and names a reused native run when qualified; each successor workcell retains first failures and its original artifact custody. The source-exact protected/private boundary is unchanged.

## Preserved first real selective-reuse RED and corrective lookup

The first targeted regression at PR head `f13c2e863df35f198b0224b13a486d6cf2340cb7`
changed only `qualification/equine/kinematic_reach/CI_FANOUT_REGRESSION.md`;
all eight PR workflows reran and all eight gates selected `run_native=true` despite
valid prior SHA-protected source results. Actual GitHub repository-wide Actions
listing proved those prior runs and digest-bearing artifacts exist. The original
per-workflow-file enumeration was inadequate for workcells registered only on
the PR branch. Source now enumerates **repository-wide public Actions runs**
filtered by exact `.path` plus PR/branch/base/ancestry/native jobs and
artifacts, instead of depending on that narrower workflow index. Retain the
first negative cost result; do not report savings until the next native A/B
commit proves the other seven gates actually select `run_native=false`.

## Second real source-provenance RED — live PR association is mutable

The subsequent one-workcell trial at `62da7c41e5248e5257f41cc885ff36049c0a50eb`
also legitimately ran all eleven native jobs. Independent direct readback proved
*why*: the provider's old successful AAC run `42230229378` retains immutable
`head_sha=b9ebb37211ebd03eeb9aedfdf168d10d015bcca8` and
`head_commit.id` equal to that historical SHA, but its attached
`pull_requests[0].head.sha` had moved to the then-current
`62da7c41e5248e5257f41cc885ff36049c0a50eb`! This live relation is **not**
a frozen evidence anchor. The previous gate incorrectly equated it with the
historical run's SHA. That predicate discarded real native proof despite a
correct branch-history diff and complete provider artifacts.

The corrected gate now binds historical proof to `run.head_sha ==
run.head_commit.id`, exact provider workflow path, matching public repo ID,
PR number and ref, frozen base SHA **and** verified Git parent ancestry; it
never requires the moving PR relation's head SHA to equal historical run SHA.
The adversarial corpus explicitly tests this dynamic association and refuses
forged immutable heads, cross-repository sources, changed base, bad artifacts
and other unsafe cases. Zero scientific or release authorization follows.

Future savings still require an exact-head real job-level observation that
separate unrelated workcells skipped their native steps and their checks stayed
green. Retain both failed optimization trials as first failures; do not silently
reinterpret them as cost reductions.
