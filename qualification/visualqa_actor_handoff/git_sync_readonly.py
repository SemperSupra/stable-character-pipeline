#!/usr/bin/env python3
"""READ-ONLY local Git authority snapshot for bounded slipper-jump actor.

No fetch, push, checkout, stage, branch creation, reset, cache, network,
writes, credential access or persistent host mutation. Run AFTER an explicit
human/agent-reviewed 'git fetch origin --no-tags'. Emits JSON to stdout.
Strict default requires SSH origin to exactly the public intended repository.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = "SemperSupra/stable-character-pipeline"
BASE_REF = "refs/remotes/origin/qualification/visualqa-nine-fix-original-corpus-r1-20261112"
BASE_SHA = "d470ab9566d479bf3ca3b53cf63be5ea75217b57"
AOR_PREFIX = "workcell/visualqa-male-jump-slippers"
APPROVED_SOURCE = "qualification/expanded_motion_corpus/build_motion_batches.py"
APPROVED_PREFIX = ("qualification/visualqa_slipper/", ".github/workflows/visualqa-slipper-")

def git(cwd:Path,*args:str,ok:bool=True)->tuple[int,str]:
    env=os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"]="0"
    p=subprocess.run(["git",*args],cwd=cwd,env=env,capture_output=True,text=True,
                     timeout=12,check=False)
    if ok and p.returncode:
        raise ValueError("GIT_OPERATION_FAILED:"+":".join(args)+":"+p.stderr.strip()[:160])
    return p.returncode,p.stdout.strip()

def expected_origin(raw:str,allow_local:bool=False):
    if re.fullmatch(r"git@github\.com:SemperSupra/stable-character-pipeline(?:\.git)?",raw):
        return "SSH_GITHUB_EXPECTED"
    if re.fullmatch(r"ssh://git@github\.com/SemperSupra/stable-character-pipeline(?:\.git)?",raw):
        return "SSH_GITHUB_EXPECTED"
    if allow_local and (raw.startswith("/") or raw.startswith("file://")):
        return "LOCAL_OFFLINE_TEST_ONLY"
    return "ORIGIN_NOT_AUTHORIZED_AS_SSH_PUBLIC_REPO"

def owned_path(p:str):
    return p==APPROVED_SOURCE or any(p.startswith(prefix) for prefix in APPROVED_PREFIX)

def snapshot(cwd:Path,expected_sha:str=BASE_SHA,allow_local_test_origin:bool=False):
    cwd=Path(cwd).resolve()
    _,toplevel=git(cwd,"rev-parse","--show-toplevel")
    cwd=Path(toplevel).resolve()
    _,raw_origin=git(cwd,"remote","get-url","origin")
    origin_type=expected_origin(raw_origin,allow_local_test_origin)
    _,branch=git(cwd,"branch","--show-current")
    _,head=git(cwd,"rev-parse","HEAD")
    _,dirty=git(cwd,"status","--porcelain=v1","--untracked-files=all")
    rc,base=git(cwd,"rev-parse","--verify",BASE_REF+"^{commit}",ok=False)
    if rc or not re.fullmatch("[0-9a-f]{40}",base):
        base=None
    relation="BASE_NOT_FETCHED"
    changed=[]
    if base:
        if head==base:relation="AT_BASE"
        elif git(cwd,"merge-base","--is-ancestor",base,head,ok=False)[0]==0:
            relation="AHEAD_OF_BASE"
        elif git(cwd,"merge-base","--is-ancestor",head,base,ok=False)[0]==0:
            relation="BEHIND_BASE"
        else:
            relation="DIVERGED_FROM_BASE"
        if relation in ("AHEAD_OF_BASE","AT_BASE"):
            _,lines=git(cwd,"diff","--name-only",base,head)
            changed=[p for p in lines.splitlines() if p]
    # Local untracked/unstaged source stays preserved, never parsed as a file
    # name decision; only counts and state are published to prevent secrets.
    reasons=[]
    if origin_type not in ("SSH_GITHUB_EXPECTED","LOCAL_OFFLINE_TEST_ONLY"):
        reasons.append("CHECK_SSH_ORIGIN_NO_NETWORK_MUTATION")
    if not base:reasons.append("FETCH_BASE_BEFORE_BRANCH_ACTION")
    elif base!=expected_sha:reasons.append("PINNED_BASE_SHA_DRIFT_STOP")
    if not branch:reasons.append("DETACHED_HEAD_PRESERVE_LOCAL_WORK")
    if dirty:reasons.append("DIRTY_TREE_PRESERVE_UNCOMMITTED_WORK")
    if relation=="DIVERGED_FROM_BASE":reasons.append("DIVERGED_HISTORY_NO_AUTOMATIC_REBASE")
    if relation=="BEHIND_BASE" and branch.startswith(AOR_PREFIX):
        reasons.append("OWNED_BRANCH_BEHIND_BASE_RECONCILE_FIRST")
    offscope=[p for p in changed if not owned_path(p)]
    if offscope:reasons.append("OFF_AOR_COMMIT_PATHS_REQUIRE_REVIEW")
    if branch.startswith(AOR_PREFIX):
        if not reasons:next_step="CONTINUE_OWNED_BRANCH_BOUNDED_PACKET"
        else:next_step="PRESERVE_AND_RECONCILE_PRIOR_WORK"
    elif not reasons:
        next_step="CREATE_NEW_OWNED_BRANCH_FROM_PINNED_BASE_ONLY_IF_NO_PREEXISTING_ACTOR_WORK"
    else:next_step="READ_ONLY_RECONCILIATION_NO_UNSAFE_GIT_ACTION"
    return {
      "schema":"scp.visualqa.local-actor-git-sync-readonly.v1",
      "repo":REPO,"aor_case":"male_jump_slippers",
      "baseline_ref":BASE_REF,
      "expected_pinned_sha":expected_sha,
      "fetched_remote_tracking_sha":base,
      "source_observation":"LOCAL_GIT_ONLY; FETCH_CURRENTNESS_MUST_BE_VERIFIED_SEPARATELY",
      "local_branch":branch or None,"local_head":head,
      "origin_kind":origin_type,"working_tree_clean":not bool(dirty),
      "uncommitted_entry_count":len([x for x in dirty.splitlines() if x]),
      "baseline_head_relation":relation,
      "owned_committed_changed_paths":changed,
      "off_aor_committed_paths":offscope,
      "blocking_conditions":reasons,
      "next_non_destructive_action":next_step,
      "remote_push_verified":False,"published_dle_verified":False,
      "original_negative_control_modified":None,
      "release_authorized":False
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repo-path",default=".")
    p.add_argument("--expected-sha",default=BASE_SHA)
    p.add_argument("--allow-local-test-origin",action="store_true",
                   help="Unit tests only. NEVER use for an actor's real GitHub remote.")
    a=p.parse_args()
    try:out=snapshot(Path(a.repo_path),a.expected_sha,a.allow_local_test_origin)
    except (ValueError,subprocess.TimeoutExpired) as e:
        print(json.dumps({"schema":"scp.visualqa.local-actor-git-sync-readonly.v1",
                          "status":"BLOCKED_READ_ONLY","error":str(e),
                          "remote_push_verified":False,"release_authorized":False},sort_keys=True))
        return 2
    print(json.dumps(out,sort_keys=True,indent=2))
    return 0 if not out["blocking_conditions"] else 3

if __name__=="__main__":
    sys.exit(main())
