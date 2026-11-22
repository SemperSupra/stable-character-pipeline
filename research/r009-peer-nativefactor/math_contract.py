"""Pure stdlib oracle shared by real Blender source/native factor witness."""
import math

def require(ok,reason):
    if not ok:raise ValueError(reason)

def vec(v):
    require(len(v)==3 and all(type(x) in (int,float) and math.isfinite(x) for x in v),
            "NONFINITE_WORLD_BONE")
    return [float(x) for x in v]

def step_metric(seq, dt=1/60.0):
    require(len(seq)>=3 and type(dt) in (int,float) and math.isfinite(dt) and dt>0,
            "INVALID_FIRST_KEY_SEQUENCE")
    a,b,c=(vec(q) for q in seq[:3])
    a0=[b[i]-a[i] for i in range(3)]
    a1=[c[i]-b[i] for i in range(3)]
    return {"first_delta_xyz_m":[round(q,9) for q in a0],
            "next_delta_xyz_m":[round(q,9) for q in a1],
            "first_3d_speed_mps":round(math.dist(a,b)/dt,6),
            "next_3d_speed_mps":round(math.dist(b,c)/dt,6),
            "first_xy_speed_mps":round(math.hypot(a0[0],a0[1])/dt,6),
            "next_xy_speed_mps":round(math.hypot(a1[0],a1[1])/dt,6)}

def summarize_channels(curves):
    summary=[]
    for curve in curves:
        points={int(round(float(k.co.x))):float(k.co.y)
                for k in curve.keyframe_points
                if abs(float(k.co.x)-round(float(k.co.x)))<1e-5 and
                int(round(float(k.co.x))) in (0,1,2)}
        if len(points)!=3:continue
        d01=points[1]-points[0];d12=points[2]-points[1]
        require(all(math.isfinite(t) for t in (d01,d12)),
                "SOURCE_ACTION_NONFINITE_FIRST_KEYS")
        summary.append({"path":str(curve.data_path),
                        "array_index":int(curve.array_index),
                        "first_abs_key_delta":round(abs(d01),9),
                        "next_abs_key_delta":round(abs(d12),9)})
    require(len(summary)>=10,"SOURCE_ACTION_FIRST_KEYS_INSUFFICIENT")
    order=sorted(summary,key=lambda x:-x["first_abs_key_delta"])
    return {"inspected_animated_and_constant_channels":len(summary),
            "top_12_first_key_channel_deltas":order[:12],
            "first_key_nonzero_channels":sum(x["first_abs_key_delta"]>1e-6 for x in summary),
            "next_key_nonzero_channels":sum(x["next_abs_key_delta"]>1e-6 for x in summary),
            "values_mixed_units_no_raw_norm_conclusion":True}
