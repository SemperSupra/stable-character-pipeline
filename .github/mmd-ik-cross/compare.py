#!/usr/bin/env python3
"""G10d fail-closed two-engine IK goal-distance parity report."""
import argparse
import json
import math
from pathlib import Path


def main():
    p=argparse.ArgumentParser()
    for n in ("blender","direct","out"):
        p.add_argument("--"+n,required=True,type=Path)
    a=p.parse_args()
    a.out.parent.mkdir(parents=True,exist_ok=True)
    b=json.loads(a.blender.read_text())
    d=json.loads(a.direct.read_text())
    assert b["status"]=="PASS_REAL_BLENDER_MMD_IK_CONSTRAINT_AND_GOAL_MOTION"
    assert d["status"]=="PASS_IK_TARGET_TRACKING"
    assert b["real_ik_constraint_count"]>=1
    frames={}
    passed=True
    for frame in ("0","15","30"):
        bx=b["samples"][frame]
        dx=d["ik_enabled"][frame]
        bf=bx["error"]
        df=dx["error"]
        # First-principles cross-engine foot goal checking.
        # Both exporters use scale 1.0 on the original fixed source PMX/VMD.
        if not (math.isfinite(bf) and math.isfinite(df)):
            raise AssertionError("nonfinite solver errors")
        delta=abs(bf-df)
        frame_pass=(bf<.05 and delta<.05) if frame!="0" else (bf<.05 and df<.05)
        if not frame_pass:
            passed=False
        frames[frame]={"blender_error":bf,"independent_error":df,
                        "absolute_error_delta":delta,"passed":frame_pass}
    receipt={
      "schema":"scp.mmd.ik.two-engine-contact.v1",
      "status":"PASS_BLENDER_VS_DIRECT_IK_CONTACT_PARITY" if passed else "FAIL_BLENDER_VS_DIRECT_IK_CONTACT_PARITY",
      "passes":passed,
      "source_fixture":"self-authored four-bone two-link MMD PMX, VMD +0.35,+0.2 in source units",
      "frames":frames,
      "acceptance_max_error":.05,
      "acceptance_max_delta":.05,
      "first_failure":"none" if passed else next(f for f in ("0","15","30") if not frames[f]["passed"]),
      "note":"Independent Blender IK imported successfully does not imply same evaluated limb goal contact as MMD-aware direct solver; no native MMD engine baseline",
      "unqualified":["MMD engine CCD parity","ground/rigid-body collisions","natural gait","human retargeting"]
    }
    a.out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print(json.dumps(receipt,sort_keys=True),flush=True)
    if not passed:
        raise AssertionError("cross-engine imported foot IK misses source goal; see preserved JSON for first failure")


if __name__=="__main__":
    main()
