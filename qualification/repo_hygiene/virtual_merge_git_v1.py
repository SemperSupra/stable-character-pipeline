"""Public Git-only source-preservation dry runs. Never checkout, merge, push or edit refs on server."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone

REPO = "SemperSupra/stable-character-pipeline"
SHA = re.compile(r"^[a-f0-9]{40}$")
CASES = (
    (95, 90, "29691e4213d837d29f68741318de3a3dbda2a392", "98776b16021bf447822794d74684942e451bf15a", "1967886686d008f8db33e5c90328928d5fe944ed"),
    (117, 116, "7afc9dfb5a70736412347d2c9316d652583f8458", "c650eab0f2cb8696aedf52500744a353b86a7b1a", "6ec5e6a4286607c9c9ce2da8aa7df35a37f6ceb4"),
    (119, 118, "da9744445e679bd611e183447db14943dd061619", "7a821e97418e2cdce8bc6ea95db1ae0ca9cb8f67", "e54505f584e419ee3eec8b5b1a94e8e3cc274c22"),
    (332, 325, "672edf4842a409deb1e10d573148e292ec05351d", "8f07eca9ebc20e50543b1559f7a0da6a7a40341a", "6165a21bea3a93201da057def377cc14f5fc4283"),
)


def git(*args: str, timeout: int = 180, cwd: str | None = None) -> bytes:
    completed = subprocess.run(["git", *args], cwd=cwd, capture_output=True, timeout=timeout, check=False)
    if completed.returncode != 0:
        raise RuntimeError("GIT_QUALIFICATION_FAILED:" + " ".join(args[:3]) + ":" + completed.stderr.decode("utf-8", "replace")[-500:])
    return completed.stdout


def strict_paths(raw: bytes) -> list[str]:
    if not raw:
        return []
    if raw[-1] != 0:
        raise ValueError("UNTERMINATED_GIT_PATH_LIST")
    paths = [x.decode("utf-8", "strict") for x in raw[:-1].split(b"\0")]
    for path in paths:
        if not path or path.startswith("/") or "\\" in path or any(p in ("", ".", "..") for p in path.split("/")):
            raise ValueError("INVALID_GIT_SOURCE_PATH")
    if len(paths) != len(set(paths)):
        raise ValueError("DUPLICATE_GIT_SOURCE_PATH")
    return sorted(paths)


def changed_paths(base: str, tip: str, cwd: str | None = None) -> list[str]:
    return strict_paths(git("diff", "--no-renames", "--name-only", "-z", base, tip, cwd=cwd))


def tree_paths(tree_sha: str, cwd: str | None = None) -> list[str]:
    raw = git("ls-tree", "-r", "-z", tree_sha, cwd=cwd)
    rows = [part.split(b"\t", 1) for part in raw[:-1].split(b"\0")]
    paths = strict_paths(b"\0".join(row[1] for row in rows) + b"\0")
    lower: dict[str, str] = {}
    universe = set(paths)
    for path in paths:
        key = path.casefold()
        if key in lower and lower[key] != path:
            raise ValueError("CASE_FOLD_SOURCE_PATH_COLLISION")
        lower[key] = path
        parts = path.split("/")
        for index in range(1, len(parts)):
            if "/".join(parts[:index]) in universe:
                raise ValueError("FILE_DIRECTORY_SOURCE_PATH_COLLISION")
    return paths


def inspect(parent: str, child: str, historical_base: str, cwd: str | None = None) -> dict[str, object]:
    if any(not SHA.fullmatch(s) for s in (parent, child, historical_base)):
        raise ValueError("UNTRUSTED_SOURCE_SHA")
    if git("merge-base", parent, child, cwd=cwd).decode().strip() != historical_base:
        raise ValueError("CHANGED_GIT_MERGE_BASE")
    pc = changed_paths(historical_base, parent, cwd)
    cc = changed_paths(historical_base, child, cwd)
    if set(pc) & set(cc):
        raise ValueError("OVERLAPPING_SOURCE_CHANGED_PATH")
    output = git("merge-tree", "--write-tree", parent, child, cwd=cwd).decode("ascii", "strict").splitlines()
    if not output or not SHA.fullmatch(output[0]):
        raise ValueError("GIT_MERGE_TREE_DID_NOT_RETURN_TREE")
    merged = output[0]
    for path in pc:
        git("diff", "--quiet", parent, merged, "--", path, cwd=cwd)
    for path in cc:
        git("diff", "--quiet", child, merged, "--", path, cwd=cwd)
    if changed_paths(historical_base, merged, cwd) != sorted(set(pc) | set(cc)):
        raise ValueError("VIRTUAL_TREE_CHANGED_SET_NOT_SOURCE_UNION")
    leaves = tree_paths(merged, cwd)
    return {"historical_base": historical_base, "current_parent": parent, "current_child": child,
            "virtual_git_tree_sha": merged, "parent_changed": pc, "child_changed": cc,
            "virtual_file_count": len(leaves), "disposition": "GIT_MERGE_TREE_NO_LOSS_REVIEW_HOLD",
            "mutations": 0, "owner_approval": False}


def main() -> None:
    if os.environ.get("GITHUB_REPOSITORY") != REPO:
        raise ValueError("UNTRUSTED_PUBLIC_REPOSITORY_CONTEXT")
    output_dir = Path(os.environ["RUNNER_TEMP"]) / "r009-hygiene"
    if not output_dir.is_dir():
        raise ValueError("EXISTING_HYGIENE_EVIDENCE_DIRECTORY_REQUIRED")
    head_before = git("rev-parse", "HEAD").decode().strip()
    status_before = git("status", "--porcelain", "-z")
    refs = sorted({n for child, parent, *_ in CASES for n in (child, parent)})
    args = [f"+refs/pull/{n}/head:refs/remotes/r009-hygiene/{n}" for n in refs]
    git("fetch", "--no-tags", "--depth=1000", "origin", *args, timeout=240)
    results = []
    for child_n, parent_n, old, parent, child in CASES:
        if git("rev-parse", f"refs/remotes/r009-hygiene/{parent_n}").decode().strip() != parent:
            raise ValueError("PARENT_HEAD_MOVED_REJECT_STALE_PROOF")
        if git("rev-parse", f"refs/remotes/r009-hygiene/{child_n}").decode().strip() != child:
            raise ValueError("CHILD_HEAD_MOVED_REJECT_STALE_PROOF")
        result = inspect(parent, child, old)
        result.update({"child_pr": child_n, "parent_pr": parent_n})
        results.append(result)
    if git("rev-parse", "HEAD").decode().strip() != head_before or git("status", "--porcelain", "-z") != status_before:
        raise ValueError("WORKING_TREE_OR_CHECKOUT_MUTATED")
    report = {"schema": "scp.r009.disposable_git_merge_tree.v1", "repo": REPO,
              "as_of": datetime.now(timezone.utc).date().isoformat(),
              "complete": True, "case_count": len(results), "results": results,
              "mutations": 0, "owner_approval": False,
              "verdict": "FOUR_DISJOINT_SOURCE_MERGE_TREE_CANDIDATES_HELD"}
    data = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    receipt = output_dir / "virtual_git_merge_v1.json"
    with receipt.open("xb") as file:
        file.write(data)
    print("R009_GIT_MERGE_TREE_CHECK", json.dumps({"cases": len(results), "output_sha256": hashlib.sha256(data).hexdigest(),
                                                   "leaf_counts": [x["virtual_file_count"] for x in results], "mutations": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
