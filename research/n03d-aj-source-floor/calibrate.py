"""N03D-AJ: exact same-clock original BVH toe vs evaluated CC0 shoe vertical calibration.

Two possible rest-X shoe-side assignments, no anatomical certainty. Train-only
constant vertical offset then heldout residual/candidate support diagnostic.
Never infer source ground or force contact from joint minima.
"""
import hashlib,json,math,statistics

SOURCES=("L","R")
SHOES=("rest_local_x_negative","rest_local_x_positive")
ACTORS=("AsterOriginal","JuniperOriginal")
N=72
def require(ok,why):
    if not ok:raise ValueError(why)
def valid(x):
    require(type(x) in (float,int) and math.isfinite(x) and abs(x)<100,"NONFINITE")
    return float(x)
def median(x):
    return round(statistics.median(x),6) if x else None
def p95_abs(x):
    v=sorted(abs(y) for y in x)
    return round(v[min(len(v)-1,math.ceil(.95*len(v))-1)],6) if v else None
def candidate(rows,n):
    """Source near-low slow toe+ankle, not plantar ground truth."""
    if n+4>=360:return False
    low=min(valid(r["source_toe"][1]) for r in rows)
    for i in range(n,n+5):
        r=rows[i]
        if valid(r["source_toe"][1])-low>.020:return False
        if i<n+4:
            next_row=rows[i+1]
            for bone in ("source_ankle","source_toe"):
                a,b=r[bone],next_row[bone]
                if math.hypot(valid(a[0])-valid(b[0]),valid(a[2])-valid(b[2]))*60>.08:
                    return False
    return True
def score(source,shoe,source_mask,train):
    x=[shoe[i]-source[i] for i in range(N)]
    bias=statistics.median(x[:36] if train else x)
    resid=[v-bias for v in x]
    heldout=resid[36:]
    indices=[i for i in range(36,N) if source_mask[i]]
    return {
        "fit_population":"TRAIN_ONLY_ALL_SOURCE_SAMPLES" if train else "ALL_FOR_CONTROL",
        "fit_source_samples":36 if train else N,
        "source_offset_target_minus_toe_y_m":round(bias,6),
        "heldout_abs_p95_m":p95_abs(heldout),
        "heldout_median_error_m":median(heldout),
        "heldout_source_low_slow_samples":len(indices),
        "heldout_source_candidate_target_shoe_min_z_p50_m":median([shoe[i] for i in indices]),
        "heldout_source_candidate_vertical_abs_p95_m":p95_abs([resid[i] for i in indices]),
        "shoe_reference_z_is_true_ground":False
    }
def evaluate(trace,ac):
    expected=hashlib.sha256((json.dumps(trace,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()).hexdigest()
    require(trace.get("schema")=="scp.n03d-g.evaluated-foot-contact-observer.v1" and
            trace.get("source_class")=="ORIGINAL_FICTIONAL_CC0" and
            trace.get("frame_rate_hz")==24 and trace.get("sample_count_per_side")==143 and
            trace.get("heel_toe_anatomy_verified") is False and trace.get("mvp_accepted") is False,
            "SHOE_TRACE_AUTHORITY")
    require(ac.get("schema")=="scp.n03d-ac.matched-source-to-bone-60hz.v1" and
            ac.get("source_class")=="ORIGINAL_FICTIONAL_CC0" and
            ac.get("source_scene_sha256")==trace.get("source_scene_sha256") and
            ac.get("source_shoe_trace_sha256")==expected and
            ac.get("source_motion_changed") is False and ac.get("mvp_accepted") is False,
            "JOIN_OR_SOURCE_RIGHTS")
    ashoe={a["actor"]:a for a in trace.get("actors",[])}
    asource={a["name"]:a for a in ac.get("actors",[])}
    require(set(ashoe)==set(ACTORS) and len(trace["actors"])==2 and
            set(asource)==set(ACTORS) and len(ac["actors"])==2,
            "SOURCE_ACTORS")
    out=[]
    for name in ACTORS:
        src=asource[name];dst=ashoe[name]
        require(src.get("sides") and set(src["sides"])==set(SOURCES) and
                set(dst.get("sides",{}))==set(SHOES) and dst.get("native_bones")==163,
                "RIG_OR_SIDE")
        src_y={};src_mask={};shoe_z={}
        for side in SOURCES:
            rows=src["sides"][side]
            require(len(rows)==360,"SOURCE_60HZ_LENGTH")
            for n,r in enumerate(rows):
                require(r.get("index")==n and abs(valid(r.get("time_s"))-n/60)<1e-7,
                        "SOURCE_CLOCK")
            src_y[side]=[valid(rows[5*k]["source_toe"][1]) for k in range(N)]
            src_mask[side]=[candidate(rows,5*k) for k in range(N)]
        for side in SHOES:
            rows=dst["sides"][side]["samples"]
            require(len(rows)==143,"SHOE_24HZ_LENGTH")
            for j,r in enumerate(rows):
                require(abs(valid(r["t_s"])-j/24)<1e-7,"SHOE_CLOCK")
                valid(r["z_m"])
            shoe_z[side]=[valid(rows[2*k]["z_m"]) for k in range(N)]
        comparisons=[]
        for mapping_name,pairing in [
            ("REST_X_POS_IS_LEFT",{"L":SHOES[1],"R":SHOES[0]}),
            ("REST_X_NEG_IS_LEFT",{"L":SHOES[0],"R":SHOES[1]})
        ]:
            sub={}
            for side in SOURCES:
                metrics=score(src_y[side],shoe_z[pairing[side]],src_mask[side],True)
                # Explicit control, evaluates same heldout with all-sample fit.
                in_sample=score(src_y[side],shoe_z[pairing[side]],src_mask[side],False)
                sub[side]={"mapped_shoe_partition":pairing[side],"train_fit":metrics,
                           "all_sample_fit_CONTROL_LEAKAGE_NOT_FOR_ADOPTION":in_sample}
            valid_metric=[sub[s]["train_fit"]["heldout_abs_p95_m"] for s in SOURCES]
            comparisons.append({"mapping":mapping_name,"sides":sub,
                                "mean_heldout_abs_p95_m":round(sum(valid_metric)/2,6),
                                "source_joint_equals_sole":False})
        out.append({"actor":name,"source_toe_y_min_m":{s:round(min(v),6) for s,v in src_y.items()},
                    "shoe_reference_z_min_m":{s:round(min(v),6) for s,v in shoe_z.items()},
                    "source_candidate_total_aligned":{s:sum(v) for s,v in src_mask.items()},
                    "clock":"EXACT_COMMON_12HZ_72_POINTS",
                    "alignment":"target_24hz_even_index_2k__source_60hz_index_5k",
                    "train_sample_indices":[0,35],"heldout_sample_indices":[36,71],
                    "sides_anatomically_identified":False,"source_ground_measured":False,
                    "comparisons":comparisons})
    return {"schema":"scp.n03d-aj.source-to-shoe-ground-bias-control.v1",
            "source_scene_sha256":trace["source_scene_sha256"],
            "source_shoe_trace_sha256":expected,
            "source_class":"ORIGINAL_FICTIONAL_CC0",
            "source_scene_mutated":False,
            "source_floor_calibrated":False,
            "shoe_anatomy_calibrated":False,
            "motion_physically_actuated":False,"mvp_accepted":False,
            "status":"HOLD","actors":out}
def independent(doc):
    require(doc.get("schema")=="scp.n03d-aj.source-to-shoe-ground-bias-control.v1" and
            doc.get("status")=="HOLD" and doc.get("source_class")=="ORIGINAL_FICTIONAL_CC0" and
            doc.get("source_scene_mutated") is False and
            doc.get("source_floor_calibrated") is False and
            doc.get("shoe_anatomy_calibrated") is False and
            doc.get("motion_physically_actuated") is False and doc.get("mvp_accepted") is False,
            "FORGED_CONTACT_OR_RELEASE")
    require(len(doc.get("actors",[]))==2 and
            set(a["actor"] for a in doc["actors"])==set(ACTORS),"ACTOR_COUNT")
    for a in doc["actors"]:
        require(a.get("clock")=="EXACT_COMMON_12HZ_72_POINTS" and
                a.get("train_sample_indices")==[0,35] and
                a.get("heldout_sample_indices")==[36,71] and
                a.get("source_ground_measured") is False and
                a.get("sides_anatomically_identified") is False,"CLOCK_OR_FALSE_ANATOMY")
        c=a.get("comparisons")
        require(len(c)==2 and set(v["mapping"] for v in c)=={"REST_X_POS_IS_LEFT","REST_X_NEG_IS_LEFT"},
                "ASSIGNMENT_FACTORIAL")
        for v in c:
            require(set(v["sides"])==set(SOURCES) and v["source_joint_equals_sole"] is False,
                    "SEMANTIC_MISMATCH")
            for s in SOURCES:
                t=v["sides"][s]["train_fit"]
                require(t["fit_source_samples"]==36 and
                        t["fit_population"]=="TRAIN_ONLY_ALL_SOURCE_SAMPLES" and
                        t["shoe_reference_z_is_true_ground"] is False,
                        "LEAKAGE_OR_FALSE_GROUND")
                for k in ("source_offset_target_minus_toe_y_m","heldout_abs_p95_m"):
                    require(valid(t[k])==t[k],"NUMERIC_CONTROL")
    return "HOLD"
