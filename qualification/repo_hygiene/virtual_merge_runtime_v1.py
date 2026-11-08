"""Replay strictly local unit suites on disposable public Git merge-tree contents."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile

REPO = "SemperSupra/stable-character-pipeline"
EXPECTED = {95: 90, 117: 116, 119: 118, 332: 325}
RUN_CHILDREN = (95, 117, 119)


def process(args: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None,
            timeout: int = 90, cap: int = 8 << 20) -> dict[str, object]:
    proc = subprocess.run(args, cwd=cwd, env=env, capture_output=True, timeout=timeout, check=False)
    if proc.returncode or len(proc.stdout) > cap or len(proc.stderr) > cap:
        msg = (proc.stderr or proc.stdout)[-350:].decode("utf-8", "replace")
        raise RuntimeError(f"COMBINED_TREE_TEST_RED:{args[0]}:{args[1] if len(args)>1 else ''}:{msg}")
    return {"command": " ".join(args[:4]), "exit_status": 0,
            "stdout_sha256": hashlib.sha256(proc.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(proc.stderr).hexdigest()}


def unpack_git_tree(tree_sha: str, dst: Path) -> None:
    if len(tree_sha) != 40 or any(c not in "0123456789abcdef" for c in tree_sha):
        raise ValueError("INVALID_VIRTUAL_TREE_SHA")
    proc = subprocess.run(["git", "archive", "--format=tar", tree_sha], capture_output=True, timeout=45, check=True)
    if len(proc.stdout) > 64 << 20:
        raise ValueError("GIT_ARCHIVE_TOO_LARGE")
    with tarfile.open(fileobj=io.BytesIO(proc.stdout)) as archive:
        for member in archive.getmembers():
            parts = Path(member.name).parts
            if not parts or any(p in ("", ".", "..") for p in parts) or Path(member.name).is_absolute():
                raise ValueError("UNSAFE_ARCHIVE_MEMBER_PATH")
            if not (member.isfile() or member.isdir()):
                raise ValueError("UNSAFE_ARCHIVE_MEMBER_TYPE")
        archive.extractall(dst, filter="data")


def main() -> None:
    if os.environ.get("GITHUB_REPOSITORY") != REPO:
        raise ValueError("WRONG_PUBLIC_REPOSITORY")
    root = Path(os.environ["RUNNER_TEMP"]) / "r009-hygiene"
    state_path = root / "virtual_git_merge_v1.json"
    state = json.loads(state_path.read_text())
    if state.get("schema") != "scp.r009.disposable_git_merge_tree.v1" or not state.get("complete") or state.get("mutations") != 0 or state.get("owner_approval") or state.get("case_count") != 4:
        raise ValueError("UNQUALIFIED_GIT_MERGE_TREE_SOURCE")
    source = {c["child_pr"]: c for c in state["results"]}
    if set(source) != set(EXPECTED) or any(source[c]["parent_pr"] != EXPECTED[c] or source[c]["disposition"] != "GIT_MERGE_TREE_NO_LOSS_REVIEW_HOLD" for c in EXPECTED):
        raise ValueError("STALE_OR_UNEXPECTED_SOURCE_TRIPLET")
    clean_env = os.environ.copy()
    for key in ("GITHUB_TOKEN", "GH_TOKEN", "OPENAI_API_KEY"):
        clean_env.pop(key, None)
    clean_env.update({"GOPROXY": "off", "GOSUMDB": "off", "GOTOOLCHAIN": "local", "GOFLAGS": "-mod=readonly",
                      "PYTHONDONTWRITEBYTECODE": "1", "HTTP_PROXY": "http://127.0.0.1:1",
                      "HTTPS_PROXY": "http://127.0.0.1:1", "ALL_PROXY": "http://127.0.0.1:1",
                      "NO_PROXY": "localhost,127.0.0.1,::1"})
    results = []
    for child in RUN_CHILDREN:
        with tempfile.TemporaryDirectory(prefix=f"r009-combined-{child}-", dir=os.environ["RUNNER_TEMP"]) as temp:
            trial = Path(temp)
            unpack_git_tree(source[child]["virtual_git_tree_sha"], trial)
            receipts = []
            if child == 95:
                directory = trial / "qualification/walk_w13"
                env = clean_env | {"GO111MODULE": "off"}
                receipts.append(process(["go", "test", "-race", "-count=1", "."], cwd=directory, env=env))
                receipts.append(process(["go", "vet", "."], cwd=directory, env=env))
                receipts.append(process(["python3", "-B", "-m", "unittest", "-v", "test_independent_ik"], cwd=directory, env=env))
                go_out, py_out, joined = (trial / n for n in ("go-ik.json", "python-ik.json", "join-ik.json"))
                receipts.append(process(["go", "run", ".", "-source", "fixtures.json", "-out", str(go_out)], cwd=directory, env=env))
                receipts.append(process(["python3", "-B", "independent_ik.py", "--source", "fixtures.json", "--out", str(py_out)], cwd=directory, env=env))
                receipts.append(process(["python3", "-B", "join_verify.py", str(go_out), str(py_out), "fixtures.json", str(joined)], cwd=directory, env=env))
                if json.loads(joined.read_text()).get("status") != "PASS_GO_VS_PYTHON_3D_IK_NUMERICAL_PARITY":
                    raise ValueError("COMBINED_IK_ORACLE_DID_NOT_JOIN")
            else:
                directory = trial / "research/providers"
                receipts.append(process(["go", "test", "-race", "-count=1", "./..."], cwd=directory, env=clean_env, timeout=160))
                receipts.append(process(["go", "vet", "./..."], cwd=directory, env=clean_env, timeout=90))
            results.append({"child_pr": child, "parent_pr": EXPECTED[child],
                            "virtual_git_tree_sha": source[child]["virtual_git_tree_sha"],
                            "checks": receipts, "local_suites": "PASS", "mutations": 0,
                            "external_provider_downloads": "NOT_RUN", "owner_merge_approval": False})
    report = {"schema": "scp.r009.disposable_merged_runtime.v1", "repo": REPO,
              "cases_tested": 3, "results": results, "not_rerun": [332],
              "no_new_external_media_or_provider_download": True,
              "mutations": 0, "owner_approval": False,
              "verdict": "THREE_PUBLIC_SOURCE_MERGED_LOCAL_SUITES_PASS_REVIEW_HOLD"}
    data = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode()
    with (root / "virtual_git_combined_runtime_v1.json").open("xb") as file:
        file.write(data)
    print("R009_COMBINED_RUNTIME_PASS", json.dumps({"cases": len(results),
                                                     "checks": [len(r["checks"]) for r in results],
                                                     "output_sha256": hashlib.sha256(data).hexdigest(),
                                                     "mutations": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
