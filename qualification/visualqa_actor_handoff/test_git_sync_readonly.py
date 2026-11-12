"""Offline tests for non-destructive local actor Git reconciliation.

All Git repositories are in a Disposable TemporaryDirectory; no user's real
origin, home dir or persistent checkout is modified. No network access.
"""
from __future__ import annotations
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from git_sync_readonly import BASE_REF, REPO, snapshot, main

def git(path:Path,*args:str):
    p=subprocess.run(["git",*args],cwd=path,capture_output=True,text=True,timeout=12)
    if p.returncode:
        raise AssertionError(f"test git {args}: {p.stderr}")
    return p.stdout.strip()

class GitActorAORTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="scp-disposable-aor-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.remote=self.root/"remote.git"
        git(self.root,"init","--bare",str(self.remote))
        self.local=self.root/"local"
        git(self.root,"clone",str(self.remote),str(self.local))
        git(self.local,"config","user.name","Disposable Test Actor")
        git(self.local,"config","user.email","test-actor@invalid.example")
        (self.local/"seed.txt").write_text("immutable original-rights baseline\n")
        git(self.local,"add","seed.txt")
        git(self.local,"commit","-m","fixture: baseline")
        self.base=git(self.local,"rev-parse","HEAD")
        git(self.local,"push","origin","HEAD:refs/heads/qualification/visualqa-nine-fix-original-corpus-r1-20261112")
        git(self.local,"fetch","origin","--no-tags")
        self.assertEqual(git(self.local,"rev-parse",BASE_REF),self.base)

    def test_no_unsafe_action_in_clean_snapshot(self):
        before=(git(self.local,"rev-parse","HEAD"),git(self.local,"status","--porcelain"),
                git(self.local,"branch","--show-current"))
        got=snapshot(self.local,expected_sha=self.base,allow_local_test_origin=True)
        after=(git(self.local,"rev-parse","HEAD"),git(self.local,"status","--porcelain"),
               git(self.local,"branch","--show-current"))
        self.assertEqual(before,after)
        self.assertEqual(got["baseline_head_relation"],"AT_BASE")
        self.assertEqual(got["blocking_conditions"],[])
        self.assertEqual(got["origin_kind"],"LOCAL_OFFLINE_TEST_ONLY")
        self.assertTrue(got["next_non_destructive_action"].startswith("CREATE_NEW_OWNED_BRANCH"))
        self.assertFalse(got["remote_push_verified"])
        self.assertFalse(got["release_authorized"])

    def test_missing_explicit_fetch_fails_closed(self):
        git(self.local,"update-ref","-d",BASE_REF)
        got=snapshot(self.local,expected_sha=self.base,allow_local_test_origin=True)
        self.assertIn("FETCH_BASE_BEFORE_BRANCH_ACTION",got["blocking_conditions"])
        self.assertEqual(got["baseline_head_relation"],"BASE_NOT_FETCHED")
        self.assertIsNone(got["fetched_remote_tracking_sha"])

    def test_remote_authority_drift_stops(self):
        got=snapshot(self.local,expected_sha="0"*40,allow_local_test_origin=True)
        self.assertIn("PINNED_BASE_SHA_DRIFT_STOP",got["blocking_conditions"])

    def test_dirty_untracked_files_preserved(self):
        (self.local/"private-progress.txt").write_text("never delete or stash")
        got=snapshot(self.local,expected_sha=self.base,allow_local_test_origin=True)
        self.assertIn("DIRTY_TREE_PRESERVE_UNCOMMITTED_WORK",got["blocking_conditions"])
        self.assertFalse(got["working_tree_clean"])
        self.assertEqual((self.local/"private-progress.txt").read_text(),"never delete or stash")
        self.assertNotIn("private-progress.txt",json.dumps(got)) # don't leak untracked file name

    def test_allowed_owned_branch_local_commits_are_detected(self):
        git(self.local,"switch","-c","workcell/visualqa-male-jump-slippers-r1-20261112")
        path=self.local/"qualification"/"visualqa_slipper"
        path.mkdir(parents=True)
        (path/"original-control.json").write_text("{}")
        git(self.local,"add","qualification/visualqa_slipper/original-control.json")
        git(self.local,"commit","-m","test: on AOR")
        head=git(self.local,"rev-parse","HEAD")
        got=snapshot(self.local,expected_sha=self.base,allow_local_test_origin=True)
        self.assertEqual(got["local_head"],head)
        self.assertEqual(got["baseline_head_relation"],"AHEAD_OF_BASE")
        self.assertEqual(got["blocking_conditions"],[])
        self.assertEqual(got["owned_committed_changed_paths"],["qualification/visualqa_slipper/original-control.json"])
        self.assertEqual(got["next_non_destructive_action"],"CONTINUE_OWNED_BRANCH_BOUNDED_PACKET")

    def test_off_aor_paths_fail_closed(self):
        git(self.local,"switch","-c","workcell/visualqa-male-jump-slippers-r1-20261112")
        (self.local/"unrelated-cartwheel.txt").write_text("do not claim ownership")
        git(self.local,"add","unrelated-cartwheel.txt")
        git(self.local,"commit","-m","test: out of AOR")
        got=snapshot(self.local,expected_sha=self.base,allow_local_test_origin=True)
        self.assertIn("OFF_AOR_COMMIT_PATHS_REQUIRE_REVIEW",got["blocking_conditions"])
        self.assertEqual(got["off_aor_committed_paths"],["unrelated-cartwheel.txt"])
        self.assertEqual(got["next_non_destructive_action"],"PRESERVE_AND_RECONCILE_PRIOR_WORK")

    def test_dirty_existing_actor_branch_not_auto_recreated(self):
        git(self.local,"switch","-c","workcell/visualqa-male-jump-slippers-r1-20261112")
        (self.local/"my-notes").write_text("unpublished")
        got=snapshot(self.local,expected_sha=self.base,allow_local_test_origin=True)
        self.assertEqual(got["next_non_destructive_action"],"PRESERVE_AND_RECONCILE_PRIOR_WORK")
        self.assertEqual(got["uncommitted_entry_count"],1)
        self.assertTrue((self.local/"my-notes").exists())

    def test_detached_head_is_a_hold(self):
        git(self.local,"checkout","--detach",self.base)
        got=snapshot(self.local,expected_sha=self.base,allow_local_test_origin=True)
        self.assertIn("DETACHED_HEAD_PRESERVE_LOCAL_WORK",got["blocking_conditions"])
        self.assertIsNone(got["local_branch"])

    def test_remote_must_be_exact_public_ssh_in_real_mode(self):
        got=snapshot(self.local,expected_sha=self.base)
        self.assertIn("CHECK_SSH_ORIGIN_NO_NETWORK_MUTATION",got["blocking_conditions"])
        self.assertNotIn(str(self.remote),json.dumps(got))

    def test_diverged_work_preserved(self):
        git(self.local,"switch","-c","workcell/visualqa-male-jump-slippers-r1-20261112")
        p=self.local/"qualification"/"visualqa_slipper"
        p.mkdir(parents=True)
        (p/"local.txt").write_text("local actor first")
        git(self.local,"add",".")
        git(self.local,"commit","-m","fixture actor progress")
        another=self.root/"other"
        git(self.root,"clone",str(self.remote),str(another))
        git(another,"config","user.name","Test Remote")
        git(another,"config","user.email","test-remote@invalid.example")
        git(another,"checkout","-b","qualification/visualqa-nine-fix-original-corpus-r1-20261112","origin/qualification/visualqa-nine-fix-original-corpus-r1-20261112")
        (another/"baseline-moving.txt").write_text("remote new authority")
        git(another,"add","baseline-moving.txt")
        git(another,"commit","-m","fixture remote moved")
        git(another,"push","origin","HEAD:refs/heads/qualification/visualqa-nine-fix-original-corpus-r1-20261112")
        git(self.local,"fetch","origin","--no-tags")
        new_sha=git(self.local,"rev-parse",BASE_REF)
        got=snapshot(self.local,expected_sha=new_sha,allow_local_test_origin=True)
        self.assertEqual(got["baseline_head_relation"],"DIVERGED_FROM_BASE")
        self.assertIn("DIVERGED_HISTORY_NO_AUTOMATIC_REBASE",got["blocking_conditions"])
        self.assertTrue((p/"local.txt").exists())

if __name__=="__main__":
    unittest.main()
