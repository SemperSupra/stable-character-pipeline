#!/usr/bin/env python3
"""Adapt the original native Blender fixed-camera skirt witness for tapered variants.

Reuses actual #342 renderer function without copying its camera, native PNG
pipeline or rig/strict-preset checks. Only augments allowed *source-pinned
experimental* variant names; no source, output or Blender correctness bypass.
"""
import sys
from pathlib import Path

# Blender's embedded Python may not inherit the process PYTHONPATH; resolve
# the exact sibling renderer from the checked-out repository, not sys.path
# guesses or a user-site plugin installation.
renderer_dir=Path(__file__).resolve().parent.parent/"human_fit_candidates"
renderer_file=renderer_dir/"render_skirt_candidate_blender.py"
if not renderer_file.is_file():
    raise RuntimeError("EXPECTED_SOURCE_ORIGINAL_RENDERER_MISSING")
sys.path.insert(0,str(renderer_dir))
import render_skirt_candidate_blender as original

VALID=("baseline","juniper_skirt_14","hem_06","hem_10")
if __name__=="__main__":
    args=sys.argv[sys.argv.index("--")+1:]
    if len(args)!=4:
        raise SystemExit("usage: -- GLB OUTPUT_DIR SHA256 VARIANT")
    src,out,sha,variant=args
    if variant not in VALID:
        raise SystemExit("UNKNOWN_JUNIPER_NATIVE_EXPERIMENT")
    # Parent original only permits declared workcell names; this isolated
    # consumer extends that known set, NOT its actual material/skin/SHA proof.
    original.CANDIDATES=tuple(sorted(set(original.CANDIDATES)|set(VALID)))
    original.render(src,out,sha,variant)
