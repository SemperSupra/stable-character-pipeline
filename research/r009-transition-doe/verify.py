"""Independent native report, fixed analytic expected displacement and held physics."""
import json
import math
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"r009-paired-envelope"))
from paired_envelope import audit,load,schedule
WINDOWS=[[40,80]]
SPEED_FACTORS={"linear":1.,"cubic":1.5,"quintic":1.875}
def expected(kind,half,tick):
    u=max(0.,1-abs(tick/32-60)/half)
    if kind=="linear":return .03*u
    if kind=="cubic":return .03*(3*u**2-2*u**3)
    if kind=="quintic":return .03*(6*u**5-15*u**4+10*u**3)
    raise ValueError(kind)
def verify(root):
    ref=load(root/"reference.json")
    assert all(abs(r["actors"]["a"]["markers"]["root"][0])<1e-9 for r in ref["rows"])
    reports={}
    for half in (10,20):
        for kind,factor in SPEED_FACTORS.items():
            label=f"{kind}-{half}";p=load(root/(label+".json"));r=audit(ref,p,WINDOWS)
            a=r["actors"]["a"];b=r["actors"]["b"];m=a["markers"]["root"]
            error=max(abs(row["actors"]["a"]["markers"]["root"][0]-expected(kind,half,row["tick"])) for row in p["rows"])
            assert r["samples"]==1600 and r["edges"]==1599 and r["last_tick"]==11488
            assert r["reference_scene_sha256"]!=r["candidate_scene_sha256"] and error<1e-6,(label,error)
            assert abs(m["max_induced_displacement_m"]["value"]-.03)<1e-6
            assert abs(a["feet"]["R"]["max_induced_displacement_m"]["value"]-.03)<1e-6
            assert a["feet"]["L"]["max_induced_displacement_m"]["value"]<1e-6
            assert b["feet"]["R"]["max_induced_displacement_m"]["value"]<1e-6
            assert b["feet"]["L"]["max_induced_displacement_m"]["value"]<1e-6
            assert m["outside_window_max_displacement_m"]<1e-6
            assert m["first_edge_candidate_speed_mps"]<1e-6 and m["last_edge_candidate_speed_mps"]<1e-6
            speed=m["max_induced_speed_mps"]["value"];acc=m["max_induced_acceleration_mps2"]["value"]
            assert abs(speed-.03*60/half*factor)<.003,(label,speed)
            assert (acc>100 if kind=="linear" else 0<acc<12),(label,acc)
            assert r["status"]=="HOLD_DIAGNOSTIC_ONLY" and not r["physical_contact_accepted"]
            reports[label]=dict(half_frames=half,peak_root_speed_mps=speed,peak_sampled_acceleration_mps2=acc,
                max_analytic_error_m=error,opposite_foot_displacement_m=a["feet"]["R"]["max_induced_displacement_m"]["value"],
                planted_proxy_displacement_m=a["feet"]["L"]["max_induced_displacement_m"]["value"],
                scene_sha256=r["candidate_scene_sha256"],samples=r["samples"])
    for kind in ("cubic","quintic"):
        a,b=reports[kind+"-10"],reports[kind+"-20"]
        assert b["peak_root_speed_mps"]<.51*a["peak_root_speed_mps"]
        assert b["peak_sampled_acceleration_mps2"]<.30*a["peak_sampled_acceleration_mps2"]
    return dict(status="PASS_NARROW_ORIGINAL_PROFILE_DOE",reference_scene_sha256=ref["scene_sha256"],
        treatments=reports,physical_contact_accepted=False,protected_likeness_used=False,mvp_accepted=False)
if __name__=="__main__":
    result=verify(Path(sys.argv[1]))
    print("R009_SMOOTH_TRANSITION_DOE",json.dumps(result,sort_keys=True,allow_nan=False))
