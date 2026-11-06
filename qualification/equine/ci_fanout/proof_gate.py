#!/usr/bin/env python3
"""Fail-closed, provider-readback native-workcell reuse gate for public PR #331.

Every pull_request check still executes. Native steps may be omitted only if a
separate, already successful *native* Actions run from the same PR/base has
unexpired provider-owned digest-bearing artifacts, and source differences since
that run are proven irrelevant to this workcell. No scientific, rights, merger,
or release acceptance follows from reused technical CI evidence.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "SemperSupra/stable-character-pipeline"
PR = 331
BRANCH = "workcell/shetland-decoded-aac-observer-20261106"
# This is the exact frozen parent, not an invitation to assume future rebases.
BASE_SHA = "574be73409714696c94028b33e8814fd7110394a"
API = "https://api.github.com/repos/" + REPO
SAFE_DIRS = {
    "av": "qualification/equine/av_observer/",
    "finite_z": "qualification/equine/finite_z/",
    "ik_ab": "qualification/equine/ik_ab/",
    "axis": "qualification/equine/axis_matrix/",
    "limit": "qualification/equine/limit_ablation/",
    "reach": "qualification/equine/kinematic_reach/",
}
WORK = {
    "equine-av-decoded-observer": ("av", ["equine-decoded-aac-observer-"]),
    "equine-av-integrated-30j-contact": ("av", ["equine-integrated-30j-native-contact-"]),
    "equine-av-native-hoof-proxy": ("av", ["equine-hoof-audio-proxy-"]),
    "equine-front-z-finite-matrix": ("finite_z", ["equine-30j-front-z-18-", "equine-30j-front-z-24-"]),
    "equine-ik-axis-matrix": ("axis", ["equine-30j-axis-x-", "equine-30j-axis-y-", "equine-30j-axis-z-"]),
    "equine-ik-limit-ablation": ("limit", ["equine-30j-ik-limit-ablation-"]),
    "equine-ik-native-ab": ("ik_ab", ["equine-30j-native-ik-ab-"]),
    "equine-ik-reachability": ("reach", ["equine-ik-reachability-"]),
}
# Conservative dependencies: a modified analyzer used by two workcells cannot
# cause one to reuse an obsolete result. Unknown paths trigger ALL native checks.
SHARED = {
    "finite_z": {"ik_ab", "reach"},
    "axis": {"ik_ab", "reach"},
    "limit": {"ik_ab", "reach"},
    "ik_ab": {"reach"},
}
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def delta_is_irrelevant(workcell: str, changed: list[str]) -> bool:
    if workcell not in WORK:
        return False
    owner = WORK[workcell][0]
    deps = {owner} | SHARED.get(owner, set())
    known_workflows = {".github/workflows/" + item + ".yml" for item in WORK}
    for path in changed:
        if not isinstance(path, str) or not path or path.startswith("/") or ".." in path.split("/"):
            return False
        if path.startswith("qualification/equine/ci_fanout/"):
            return False  # gate/policy change always forces fresh native execution
        matches = [key for key, prefix in SAFE_DIRS.items() if path.startswith(prefix)]
        if matches:
            if matches[0] in deps:
                return False
            continue
        if path in known_workflows:
            if path == ".github/workflows/" + workcell + ".yml":
                return False
            continue
        return False  # any unrecognized/untracked transitive input fails closed
    return True


def provider_proof(run: dict, jobs: list[dict], artifacts: list[dict], *, workcell: str,
                   head: str, base: str, now: dt.datetime) -> bool:
    if workcell not in WORK or not SHA_RE.fullmatch(head) or base != BASE_SHA:
        return False
    if run.get("path") != ".github/workflows/" + workcell + ".yml":
        return False
    if run.get("event") != "pull_request" or run.get("status") != "completed" or run.get("conclusion") != "success":
        return False
    if run.get("head_branch") != BRANCH or not SHA_RE.fullmatch(str(run.get("head_sha", ""))):
        return False
    p = run.get("pull_requests") or []
    if len(p) != 1 or p[0].get("number") != PR or p[0].get("head", {}).get("sha") != run["head_sha"] or p[0].get("base", {}).get("sha") != base:
        return False
    try:
        created = dt.datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        return False
    if not dt.timedelta(0) <= now - created < dt.timedelta(days=7):
        return False
    if not jobs or any(j.get("conclusion") != "success" or j.get("status") != "completed" for j in jobs):
        return False
    # Check count of native matrix jobs; no missing or skipped native lane may certify.
    if len(jobs) < len(WORK[workcell][1]):
        return False
    run_id = run.get("id")
    if not isinstance(run_id, int) or run_id <= 0:
        return False
    for prefix in WORK[workcell][1]:
        expected = prefix + str(run_id)
        found = [a for a in artifacts if a.get("name") == expected]
        if len(found) != 1:
            return False
        a = found[0]
        if a.get("expired") is not False or not isinstance(a.get("size_in_bytes"), int) or a["size_in_bytes"] <= 0 or not DIGEST_RE.fullmatch(str(a.get("digest", ""))):
            return False
    return True


def git_delta(earlier: str, latest: str) -> list[str] | None:
    if not SHA_RE.fullmatch(earlier) or not SHA_RE.fullmatch(latest):
        return None
    if subprocess.run(["git", "merge-base", "--is-ancestor", earlier, latest], capture_output=True, check=False).returncode != 0:
        return None
    p = subprocess.run(["git", "diff", "--name-only", "--no-renames", earlier, latest, "--"], capture_output=True, text=True, check=False)
    if p.returncode != 0:
        return None
    return [s for s in p.stdout.splitlines() if s]


def api_get(path: str, token: str) -> dict:
    req = urllib.request.Request(API + path,
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": "SCP-source-exact-CI-proof-gate"})
    with urllib.request.urlopen(req, timeout=12) as resp:
        if resp.status != 200:
            raise ValueError("provider returned non-success")
        body = resp.read(2 * 1024 * 1024 + 1)
        if len(body) > 2 * 1024 * 1024:
            raise ValueError("provider result over bound")
        return json.loads(body)


def qualify(workcell: str, head: str, base: str, token: str, *, api=api_get, diff=git_delta,
            now: dt.datetime | None = None) -> dict:
    result = {"schema": "scp.ci.native-proof-gate.v1", "workcell": workcell,
              "head_sha": head, "base_sha": base,
              "run_native": True, "reused_native_run_id": None,
              "reason": "run required: no independently verified identical successful native proof",
              "technical_evidence_only": True, "scientific_accepted": False,
              "rights_accepted": False, "merge_or_release_authorized": False}
    if workcell not in WORK or not SHA_RE.fullmatch(head) or base != BASE_SHA or not token:
        result["reason"] = "run required: unknown workcell/head/base or missing provider token"
        return result
    now = now or dt.datetime.now(dt.timezone.utc)
    # Repository-wide run listing covers branch-defined workflows that are not
    # registered on default main; filter exact workflow PATH and PR/branch below.
    path = "/actions/runs?event=pull_request&branch=" + urllib.parse.quote(BRANCH, safe="") + "&per_page=100"
    try:
        response = api(path, token)
        runs = response.get("workflow_runs")
        if not isinstance(runs, list) or len(runs) > 100:
            raise ValueError("bad provider run listing")
        for run in runs:
            if run.get("path") != ".github/workflows/" + workcell + ".yml":
                continue
            old = run.get("head_sha", "")
            if old == head:  # the current run cannot serve as its own independent proof
                continue
            if not isinstance(old, str) or not SHA_RE.fullmatch(old):
                continue
            delta = diff(old, head)
            if delta is None or not delta_is_irrelevant(workcell, delta):
                continue
            run_id = run.get("id")
            if not isinstance(run_id, int) or run_id <= 0:
                continue
            jobs = api("/actions/runs/" + str(run_id) + "/jobs?per_page=100", token)
            arts = api("/actions/runs/" + str(run_id) + "/artifacts?per_page=100", token)
            if jobs.get("total_count", 0) > 100 or arts.get("total_count", 0) > 100:
                continue
            if provider_proof(run, jobs.get("jobs", []), arts.get("artifacts", []),
                              workcell=workcell, head=head, base=base, now=now):
                result["run_native"] = False
                result["reused_native_run_id"] = run_id
                result["reason"] = "reused prior provider-successful native proof; unchanged workcell closure and unexpired digest-bearing artifacts"
                result["changed_file_count"] = len(delta)
                return result
    except Exception as exc:  # any uncertainty must run native, never omit it
        result["reason"] = "run required: provider/git evidence unavailable (" + type(exc).__name__ + ")"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workcell", required=True, choices=sorted(WORK))
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(Path(os.environ.get("GITHUB_EVENT_PATH", "")).read_text())
        pr = data.get("pull_request", {})
        head, base = pr.get("head", {}), pr.get("base", {})
        valid = (data.get("number") == PR and os.environ.get("GITHUB_REPOSITORY") == REPO and
                 head.get("ref") == BRANCH and base.get("sha") == BASE_SHA)
        sha = head.get("sha", "") if valid else ""
        parent = base.get("sha", "") if valid else ""
    except (ValueError, OSError, TypeError, KeyError):
        sha, parent = "", ""
    outcome = qualify(args.workcell, sha, parent, os.environ.get("GH_TOKEN", ""))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(outcome, indent=2, sort_keys=True) + "\n")
    if (path := os.environ.get("GITHUB_OUTPUT")):
        with open(path, "a", encoding="utf-8") as f:
            f.write("run_native=" + str(outcome["run_native"]).lower() + "\n")
            f.write("proof_run_id=" + str(outcome["reused_native_run_id"] or "none") + "\n")
    print("SCP_NATIVE_CI_GATE", args.workcell, "run_native=" + str(outcome["run_native"]).lower(),
          "proof_run=" + str(outcome["reused_native_run_id"] or "none"), outcome["reason"])


if __name__ == "__main__":
    main()
