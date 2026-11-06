#!/usr/bin/env python3
"""Fail-closed disposable source-combination trial, not a PR rebase or release.

Combines the exact original parametric-human parent #308 with child #336 in a
temporary Git worktree on a public runner. Preserves the parent's 72-frame BVH
v2 algorithm and native witness, and the child's guarded synthetic fitter and
workflow path. Never commits or pushes, never edits either remote source.
This trial tests static source contract and stdlib synthetic unit tests, NOT a
fresh native Blender image pass on the combined tree. Must remain SCIENCE HELD.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

WORKFLOW = ".github/workflows/r009-parametric-native-blender-v1.yml"
BVH = "qualification/parametric_humans/native_bvh_contact_v1.py"
FITTER = "qualification/parametric_humans/surface_registration_v1.py"
TESTS = (
    "test_surface_registration_v1",
    "test_surface_registration_quality",
    "test_surface_registration_metamorphic",
)
PARENT_REF = "refs/heads/qualification/r009-parametric-human-contract-v1-20261105"
CHILD_REF = "refs/heads/qualification/r009-surface-fit-synthetic-v1-20261106"
OLD_SCOPE = (
    r"^(qualification/parametric_humans/|\.github/workflows/"
    r"r009-parametric-(human-contract|native-blender)-v1\.yml$)"
)
NEW_SCOPE = (
    r"^(qualification/parametric_humans/|\.github/workflows/"
    r"(r009-parametric-(human-contract|native-blender)-v1|"
    r"r009-synthetic-surface-registration-v1)\.yml$)"
)
CHILD_TRIGGER = "      - '.github/workflows/r009-synthetic-surface-registration-v1.yml'"

ROOT = Path(__file__).resolve().parents[2]
SHA40 = re.compile(r"^[0-9a-f]{40}$")


def command(*args, cwd=ROOT, allowed=(0,)):
    p = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if p.returncode not in allowed:
        raise RuntimeError("command failed %s exit=%d stdout=%s stderr=%s" %
                           (args[:4], p.returncode, p.stdout[-800:], p.stderr[-800:]))
    return p


def source_bytes(sha, path):
    return command("git", "show", sha + ":" + path).stdout.encode()


def safe_patch(parent_text, child_text):
    """Only two exact, additive policy edits may bridge the shared workflow."""
    if parent_text.count(OLD_SCOPE) != 1 or child_text.count(NEW_SCOPE) != 1:
        raise ValueError("parent/child source-scope policy changed")
    if parent_text.count("assert bvh[\"schema\"]==\"scp.r009.original_bvh_surface_contact.v2\"") != 1:
        raise ValueError("BVH v2 parent evidence contract missing")
    if "assert bvh[\"schema\"]==\"scp.r009.original_bvh_surface_contact.v1\"" not in child_text:
        raise ValueError("child-old-native-BVH conflict no longer matches expected scenario")
    if parent_text.count("      - '.github/workflows/r009-parametric-native-blender-v1.yml'") != 1:
        raise ValueError("source trigger anchor changed")
    if CHILD_TRIGGER not in child_text or CHILD_TRIGGER in parent_text:
        raise ValueError("unexpected child source path or parent already changed")
    result = parent_text.replace(
        "      - '.github/workflows/r009-parametric-native-blender-v1.yml'",
        "      - '.github/workflows/r009-parametric-native-blender-v1.yml'\n" + CHILD_TRIGGER,
        1,
    ).replace(OLD_SCOPE, NEW_SCOPE, 1)
    if result.count(NEW_SCOPE) != 1 or result.count(CHILD_TRIGGER) != 1:
        raise ValueError("patch did not preserve child source-scope")
    if "assert bvh[\"schema\"]==\"scp.r009.original_bvh_surface_contact.v1\"" in result:
        raise ValueError("BVH downgrade introduced")
    return result


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parent = os.environ["PARENT_HEAD_PIN"]
    child = os.environ["CHILD_HEAD"]
    old_base = os.environ["OLD_PARENT_PIN"]
    output = Path(os.environ["INTEGRATION_RECEIPT"])
    if any(SHA40.fullmatch(x) is None for x in (parent, child, old_base)):
        raise ValueError("noncanonical source commit SHA")
    before_parent = command("git", "ls-remote", "origin", PARENT_REF).stdout.split()
    before_child = command("git", "ls-remote", "origin", CHILD_REF).stdout.split()
    if not before_parent or before_parent[0] != parent or not before_child or before_child[0] != child:
        raise ValueError("stale source head lease")
    command("git", "cat-file", "-e", parent + "^{commit}")
    command("git", "cat-file", "-e", child + "^{commit}")
    merge_base = command("git", "merge-base", parent, child).stdout.strip()
    if merge_base != old_base:
        raise ValueError("parent lineage changed or unexpected merge base")
    parent_native = source_bytes(parent, BVH)
    child_fitter = source_bytes(child, FITTER)
    if b'SCHEMA = "scp.r009.original_bvh_surface_contact.v2"' not in parent_native:
        raise ValueError("native BVH v2 algorithm not in current parent")
    parent_workflow = source_bytes(parent, WORKFLOW).decode()
    child_workflow = source_bytes(child, WORKFLOW).decode()
    combined_workflow = safe_patch(parent_workflow, child_workflow)

    with tempfile.TemporaryDirectory(prefix="scp-r009-integrated-") as directory:
        target = Path(directory) / "source"
        command("git", "worktree", "add", "--detach", str(target), parent)
        try:
            merger = command("git", "merge", "--no-commit", "--no-ff", child,
                             cwd=target, allowed=(0, 1))
            unresolved = command("git", "diff", "--name-only", "--diff-filter=U",
                                 cwd=target).stdout.splitlines()
            if unresolved and unresolved != [WORKFLOW]:
                raise ValueError("unexpected additional merge conflicts: %s" % unresolved)
            if merger.returncode != 0 and not unresolved:
                raise ValueError("merge failed without expected scope conflict")
            # Reconstruct from exact-parent bytes, never keep a conflict-marker
            # or blindly choose the child's older 12-frame BVH source policy.
            (target / WORKFLOW).write_text(combined_workflow)
            command("git", "add", "--", WORKFLOW, cwd=target)
            if command("git", "diff", "--name-only", "--diff-filter=U",
                       cwd=target).stdout.strip():
                raise ValueError("unresolved merge marker remains")
            if (target / BVH).read_bytes() != parent_native:
                raise ValueError("current parent native BVH producer was mutated")
            if (target / FITTER).read_bytes() != child_fitter:
                raise ValueError("child source fitter was lost during combination")
            if (target / WORKFLOW).read_text() != combined_workflow:
                raise ValueError("joint parent-native and child-scope policy differs")
            # No bpy import here; parent current native full 72-frame Blender
            # tests must still execute separately on an exact combined source.
            run = command(sys.executable, "-m", "unittest", "-v", *TESTS,
                          cwd=target / "qualification/parametric_humans")
            print("COMBINED_SYNTHETIC_SURFACE_UNIT_STDOUT", run.stdout[-1200:])
            print("COMBINED_SYNTHETIC_SURFACE_UNIT_STDERR", run.stderr[-1800:])
            observed = {
                "schema": "scp.disposable_source_integration.v1",
                "parent_pr": 308, "child_pr": 336,
                "parent_head": parent, "child_head": child, "old_base": old_base,
                "parent_native_bvh_sha256": sha256(parent_native),
                "child_surface_fitter_sha256": sha256(child_fitter),
                "composed_native_workflow_sha256": sha256(combined_workflow.encode()),
                "unresolved_conflicts": 0,
                "combined_python_synthetic_tests": "PASS",
                "parent_bvh_schema": "scp.r009.original_bvh_surface_contact.v2",
                "child_source_scope_added": True,
                "joint_native_blender_render_evaluated": False,
                "human_visual_acceptance": False,
                "real_photo_fit": "NOT_RUN",
                "scientific_anatomy": "UNKNOWN",
                "no_remote_branch_merge_or_push": True,
                "merge_release_CPE_approval": False,
                "disposition": "DISPOSABLE_COMBINED_SOURCE_SYNTHETIC_ONLY_JOINT_NATIVE_HELD"
            }
            output.write_text(json.dumps(observed, indent=2, sort_keys=True) + "\n")
            print("DISPOSABLE_PARENT_BVH_V2_AND_CHILD_SURFACE_COMBINED_SOURCE_PASS")
        finally:
            command("git", "worktree", "remove", "--force", str(target))
    after_parent = command("git", "ls-remote", "origin", PARENT_REF).stdout.split()
    after_child = command("git", "ls-remote", "origin", CHILD_REF).stdout.split()
    if not after_parent or after_parent[0] != parent or not after_child or after_child[0] != child:
        output.unlink(missing_ok=True)
        raise ValueError("source changed during disposable qualification")


if __name__ == "__main__":
    main()
