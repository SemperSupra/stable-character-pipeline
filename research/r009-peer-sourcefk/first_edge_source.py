"""Independent original 100STYLE BVH world FK first-edge falsifier, stdlib only.

Compares original source 120→121 joint velocity to nearby and first-minute
reference edges. Reuses canonical R088 parser/FK; no Blender retarget, shoe
contact, protected asset, physical GRF or MVP acceptance.
"""
import argparse
import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"r088-motion-real"))
from bvh_preflight import parse_bvh, git_blob_sha, fk, SOURCES, SOURCE_COMMIT

BLOB=SOURCES["Neutral_FW.bvh"]
JOINTS=("Hips","LeftHip","RightHip","LeftKnee","RightKnee",
        "LeftAnkle","RightAnkle","LeftToe","RightToe")


def need(ok,code):
    if not ok: raise ValueError(code)


def point(p):
    need(isinstance(p,(list,tuple)) and len(p)==3 and
         all(type(x) in (int,float) and math.isfinite(x) and abs(x)<100000 for x in p),
         "SOURCE_FK_INVALID_POINT")
    return tuple(float(x)*0.01 for x in p)  # source centimetres -> metres


def first_edge_metrics(series, *, start=120):
    """Consecutive original source world XYZ, metre-calibrated from BVH cm."""
    need(isinstance(series,list) and len(series)>=180,"SOURCE_FK_SERIES_SHORT")
    p=[point(v) for v in series]
    need(type(start) is int and 1<=start and start+60<=len(p),
         "SOURCE_FK_INVALID_FIRST_EDGE")
    def velocity(i):
        return 60.0*math.dist(p[i-1],p[i])
    speeds=[velocity(i) for i in range(start+1,start+60)]
    med=statistics.median(speeds)
    first=speeds[0]
    vector=[p[start+1][j]-p[start][j] for j in range(3)]
    return {
        "source_first_edge":str(start)+"->"+str(start+1),
        "source_first_edge_world_xyz_m":[round(v,9) for v in vector],
        "source_first_edge_3d_speed_mps":round(first,6),
        "source_first_edge_horizontal_xz_speed_mps":round(60*math.hypot(vector[0],vector[2]),6),
        "nearby_prev_edge_3d_speed_mps":round(velocity(start),6),
        "nearby_next_edge_3d_speed_mps":round(velocity(start+2),6),
        "first_59_edges_3d_speed_median_mps":round(med,6),
        "first_59_edges_3d_speed_max_mps":round(max(speeds),6),
        "first_edge_to_median_ratio":round(first/med,6) if med>1e-9 else None,
        "native_retarged_footwear_accepted":False,
        "source_joint_anatomy_verified":False,
    }


def build(path):
    need(Path(path).name=="Neutral_FW.bvh","SOURCE_100STYLE_NAME")
    raw=Path(path).read_bytes()
    need(git_blob_sha(raw)==BLOB,"SOURCE_100STYLE_BLOB_CHANGED")
    bvh=parse_bvh(raw)
    need(bvh["count"]==2400 and abs(bvh["frame_time"]-1/60)<1e-5 and
         all(name in bvh["names"] for name in JOINTS),
         "SOURCE_100STYLE_HIERARCHY_OR_CLOCK")
    # Maintain a bounded source world observation independent of the retargeter.
    series={k:[] for k in JOINTS}
    for i in range(180):
        positions=fk(bvh,i)
        for k in JOINTS:
            series[k].append(positions[k])
    diagnostics={k:first_edge_metrics(series[k]) for k in JOINTS}
    report={
        "schema":"scp.r009.peer-original-bvh-fk-start-edge-v1",
        "source_class":"ORIGINAL_PUBLIC_100STYLE_CC_BY_4",
        "source_file_not_redistributed":True,
        "source_git_commit":SOURCE_COMMIT,
        "source_git_blob_sha1":BLOB,
        "source_clock_hz":60,
        "source_full_frame_count":2400,
        "admitted_source_window_first_frame":120,
        "admitted_source_window_last_frame":479,
        "original_source_world_axes":"X horizontal, Y vertical, Z horizontal",
        "source_fk_unit_conversion":"cm * 0.01 = metres",
        "source_fk_joints":diagnostics,
        "native_retarget_equivalence_proven":False,
        "ground_contact_proven":False,
        "protected_likeness_used":False,
        "mvp_accepted":False,
        "status":"HOLD",
    }
    return report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--motion",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    result=build(a.motion)
    Path(a.out).write_text(json.dumps(result,sort_keys=True,allow_nan=False)+"\n")
    print("R009_SOURCE_FIRST_EDGE_FK_HOLD",json.dumps(result,sort_keys=True),flush=True)

if __name__=="__main__":
    main()
