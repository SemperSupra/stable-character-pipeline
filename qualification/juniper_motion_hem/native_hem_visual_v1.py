#!/usr/bin/env python3
"""Adapt the original native Blender fixed-camera skirt witness for tapered variants.

Reuses actual #342 renderer function without copying its camera, native PNG
pipeline or rig/strict-preset checks. Only augments allowed *source-pinned
experimental* variant names; no source, output or Blender correctness bypass.
"""
import sys
from pathlib import Path
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
