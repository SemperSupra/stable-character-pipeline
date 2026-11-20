"""N03D-AC: strict matched-clock causal gait trace (diagnostic, never contact proof)."""
import math
import statistics

ACTORS = ("AsterOriginal", "JuniperOriginal")
SIDES = ("L", "R")

def check(ok, message):
    if not ok:
        raise ValueError(message)

def vec(p):
    check(isinstance(p, (tuple, list)) and len(p) == 3 and all(type(v) in (int, float) and math.isfinite(v) and abs(v) < 100 for v in p), "BAD_VECTOR")
    return tuple(float(v) for v in p)

def speed(a, b, dt, axes=(0, 2)):
    return math.sqrt(sum((a[k]-b[k])**2 for k in axes))/dt

def percentile(values, q):
    if not values:
        return None
    seq=sorted(values)
    return round(seq[min(len(seq)-1, max(0, math.ceil(q*len(seq))-1))], 6)

def first_bad_run(flags, min_length=3):
    """Linear onset identification; binary refinement requires a monotone bracket."""
    start = None
    for i, bad in enumerate([*flags, False]):
        if bad and start is None:
            start = i
        elif not bad and start is not None:
            if i-start >= min_length:
                return (start, i-1)
            start = None
    return None

def evaluate(rows, hz=60, near=0.02, slow=0.08, target_slide=0.08):
    check(type(hz) is int and hz == 60 and 0 < near < 0.2 and 0 < slow <= 2 and 0 < target_slide <= 2, "BAD_PARAMETERS")
    check(isinstance(rows, list) and len(rows) == 360, "SAMPLE_COUNT")
    keys = {"index", "time_s", "source_hip", "source_ankle", "source_toe", "target_hip", "target_foot", "target_shoe_min_z"}
    for i, row in enumerate(rows):
        check(isinstance(row, dict) and set(row) == keys and row["index"] == i, "SAMPLE_SCHEMA")
        check(type(row["time_s"]) in (float, int) and math.isfinite(row["time_s"]) and abs(row["time_s"]-i/hz)<1e-7, "CLOCK_OR_INDEX")
        for name in ("source_hip","source_ankle","source_toe","target_hip","target_foot"):
            vec(row[name])
        check(type(row["target_shoe_min_z"]) in (float,int) and math.isfinite(row["target_shoe_min_z"]) and abs(row["target_shoe_min_z"])<10, "SHOE_FINITE")
    ground=min(row["source_toe"][1] for row in rows)
    toe_speeds=[]; ankle_speeds=[]; target_speeds=[]; root_speeds=[]; local_ankle=[]; local_foot=[]; eligible=[]; different=[]
    for i in range(1,len(rows)):
        a,b=rows[i-1],rows[i]; dt=b["time_s"]-a["time_s"]
        check(abs(dt-1/hz)<1e-7,"TIMEBASE")
        toe=speed(a["source_toe"],b["source_toe"],dt)
        ankle=speed(a["source_ankle"],b["source_ankle"],dt)
        target=speed(a["target_foot"],b["target_foot"],dt,axes=(0,1))
        root=speed(a["target_hip"],b["target_hip"],dt,axes=(0,1))
        source_rel_a=tuple(a["source_ankle"][k]-a["source_hip"][k] for k in range(3))
        source_rel_b=tuple(b["source_ankle"][k]-b["source_hip"][k] for k in range(3))
        target_rel_a=tuple(a["target_foot"][k]-a["target_hip"][k] for k in range(3))
        target_rel_b=tuple(b["target_foot"][k]-b["target_hip"][k] for k in range(3))
        toe_speeds.append(toe); ankle_speeds.append(ankle); target_speeds.append(target); root_speeds.append(root)
        local_ankle.append(speed(source_rel_a,source_rel_b,dt))
        local_foot.append(speed(target_rel_a,target_rel_b,dt,axes=(0,1)))
        is_candidate=(a["source_toe"][1]-ground <=near and b["source_toe"][1]-ground<=near and toe<=slow and ankle<=slow)
        eligible.append(is_candidate)
        different.append(is_candidate and target>target_slide)
    idx=[i for i,c in enumerate(eligible) if c]
    bad=first_bad_run(different,3)
    # IMPORTANT: "UNKNOWN" if no independently verified anatomical and ground contact.
    return {
       "source_contact_proven": False, "anatomical_landmarks_calibrated": False,
       "candidate_interval_count": len(idx),
       "matched_source_toe_p50_mps": percentile([toe_speeds[i] for i in idx],.5),
       "matched_source_ankle_p50_mps": percentile([ankle_speeds[i] for i in idx],.5),
       "matched_target_foot_p50_mps": percentile([target_speeds[i] for i in idx],.5),
       "matched_target_root_p50_mps": percentile([root_speeds[i] for i in idx],.5),
       "matched_source_ankle_local_p50_mps": percentile([local_ankle[i] for i in idx],.5),
       "matched_target_foot_local_p50_mps": percentile([local_foot[i] for i in idx],.5),
       "matched_target_foot_p95_mps": percentile([target_speeds[i] for i in idx],.95),
       "first_three_consecutive_source_candidate_target_slide": {"start_interval":bad[0],"end_interval":bad[1],"start_time_s":round(bad[0]/hz,6)} if bad else None,
       "threshold_candidate_mismatch_count": sum(different),
       "minimum_target_shoe_z_m": round(min(row["target_shoe_min_z"] for row in rows),6),
       "status":"HOLD",
       "causal_stage":"SOURCE_TO_TARGET_BONE_OR_ROOT_UNRESOLVED" if idx and any(different) else "UNKNOWN",
    }

def assess(report):
    check(report.get("schema") == "scp.n03d-ac.matched-source-to-bone-60hz.v1", "SCHEMA")
    check(report.get("source_class") == "ORIGINAL_FICTIONAL_CC0", "RIGHTS")
    check(report.get("source_motion_changed") is False and report.get("mvp_accepted") is False, "SOURCE_OR_ACCEPTANCE_MUTATION")
    check(isinstance(report.get("actors"),list) and len(report["actors"])==2,"ACTORS")
    found=set()
    result=[]
    for actor in report["actors"]:
        check(actor.get("name") in ACTORS and isinstance(actor.get("sides"),dict), "ACTOR")
        for side,rows in actor["sides"].items():
            check(side in SIDES and (actor["name"],side) not in found, "DUPLICATE_SIDE")
            found.add((actor["name"],side))
            result.append({"actor":actor["name"],"side":side,**evaluate(rows)})
    check(found=={(a,s) for a in ACTORS for s in SIDES}, "INCOMPLETE_FACTORIAL")
    return {"schema":"scp.n03d-ac.independent-causal-diagnosis.v1","status":"HOLD","source_contact_proven":False,"mvp_accepted":False,"results":result}
