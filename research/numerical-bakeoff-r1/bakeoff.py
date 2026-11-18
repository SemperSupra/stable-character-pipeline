#!/usr/bin/env python3
"""N01/N02 source-safe numerical falsifiers: synthetic math only, stdlib."""
import argparse, hashlib, json, math, platform
from pathlib import Path

CASES = (
    ("stiff_overdamped", 14., 1.8, .2, .002, 5),
    ("critical", 8., 1., .15, .002, 8),
    ("underdamped", 4., .7, .1, .002, 10),
)

def spring_exact(t, freq, damping, force):
    w = 2*math.pi*freq
    equilibrium = force/(w*w)
    y = -equilibrium
    if damping < 1-1e-12:
        wd = w*math.sqrt(1-damping*damping)
        return equilibrium + math.exp(-damping*w*t)*(y*math.cos(wd*t)+(damping*w*y/wd)*math.sin(wd*t))
    if damping > 1+1e-12:
        d = math.sqrt(damping*damping-1)
        r1, r2 = -w*(damping-d), -w*(damping+d)
        a = -r2*y/(r1-r2)
        return equilibrium+a*math.exp(r1*t)+(y-a)*math.exp(r2*t)
    return equilibrium+(y+w*y*t)*math.exp(-w*t)

def spring_integrate(freq, damping, interval, force, frames, method, substeps):
    p=(freq,damping,interval,force)
    if not all(math.isfinite(v) for v in p) or not(.4<=freq<=14 and .15<=damping<=1.8 and
        .001<=interval<=.2 and frames>=1 and substeps>=1):
        raise ValueError("BAD_SPRING_PARAMETERS")
    if method not in ("legacy","adaptive","rk4","exact"):
        raise ValueError("UNKNOWN_SOLVER")
    w=2*math.pi*freq
    x=v=0.
    out=[]
    for i in range(frames):
        h=interval/substeps
        for j in range(substeps):
            if method=="exact":
                x=spring_exact((i+(j+1)/substeps)*interval,freq,damping,force)
                v=0.
            elif method in ("legacy","adaptive"):
                v+=(force-2*damping*w*v-w*w*x)*h
                x+=v*h
                if method=="legacy" and abs(x)>.035:
                    x=math.copysign(.035,x)
                    if math.copysign(1.,x)==math.copysign(1.,v):
                        v=0.
            else:
                def rhs(a,b):
                    return b,force-2*damping*w*b-w*w*a
                k1x,k1v=rhs(x,v)
                k2x,k2v=rhs(x+h*k1x/2,v+h*k1v/2)
                k3x,k3v=rhs(x+h*k2x/2,v+h*k2v/2)
                k4x,k4v=rhs(x+h*k3x,v+h*k3v)
                x+=h*(k1x+2*k2x+2*k3x+k4x)/6
                v+=h*(k1v+2*k2v+2*k3v+k4v)/6
            if not math.isfinite(x) or not math.isfinite(v):
                raise ValueError("NONFINITE_INTEGRATION")
        out.append(x)
    return out

def spring_budget(freq,damping,interval):
    w=2*math.pi*freq
    stiff=w*(damping+math.sqrt(damping*damping-1)) if damping>=1 else w
    return max(10, math.ceil(stiff*interval/.75))

def n01():
    results=[]
    for name,freq,damping,interval,force,frames in CASES:
        expected=[spring_exact((i+1)*interval,freq,damping,force) for i in range(frames)]
        budget=spring_budget(freq,damping,interval)
        methods={"legacy_10":("legacy",10),"adaptive_semi":("adaptive",budget),
                 "adaptive_rk4":("rk4",budget),"closed_form":("exact",1)}
        measured={}
        for label,(method,steps) in methods.items():
            got=spring_integrate(freq,damping,interval,force,frames,method,steps)
            measured[label]={"substeps":steps,"max_error_m":max(abs(a-b) for a,b in zip(expected,got)),
                "peak_displacement_m":max(map(abs,got))}
        results.append({"fixture":name,"frequency_hz":freq,"damping_ratio":damping,
            "sample_dt_s":interval,"force_m_per_s2":force,"methods":measured})
    stiff=results[0]["methods"]
    baseline_red=stiff["legacy_10"]["max_error_m"]>.001
    challengers_good=all(v["max_error_m"]<2e-5 for row in results for k,v in row["methods"].items() if k!="legacy_10")
    return {"schema":"scp.numerics.n01.v1",
        "verdict":"PASS_NARROW" if baseline_red and challengers_good else "RED",
        "legacy_stiff_case_falsified":baseline_red,
        "challengers_within_2e_5_m":challengers_good,"cases":results,
        "note":"Permitted constant-force synthetic cases only; displacement clipping is not numerical stability"}

def strict_positive(v):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0:
        raise ValueError("BAD_PHYSICAL_MEASURAND")
    return float(v)

def edit_gate(original,changed,mode):
    if mode not in ("legacy_or","target_specific"):
        raise ValueError("UNKNOWN_EDIT_GATE")
    try:
        a,b,base_volume=(strict_positive(original[k]) for k in ("waist","height","volume"))
        c,d,e=(strict_positive(changed[k]) for k in ("waist","height","volume"))
    except (KeyError,ValueError,TypeError):
        return False
    target=100*abs(c-a)/a
    height=100*abs(d-b)/b
    volume=100*abs(e-base_volume)/base_volume
    return (target>=1.5 or (mode=="legacy_or" and volume>=1.5)) and height<=.5

def n02():
    original={"waist":.30,"height":1.70,"volume":.060}
    cases=(
        ("volume_only",original,{"waist":.30,"height":1.70,"volume":.061},False),
        ("target_edit",original,{"waist":.31,"height":1.70,"volume":.060},True),
        ("invariant_drift",original,{"waist":.31,"height":1.72,"volume":.060},False),
        ("nonfinite",original,{"waist":float("nan"),"height":1.70,"volume":.061},False),
        ("negative",original,{"waist":.31,"height":1.70,"volume":-.001},False),
        ("zero_baseline",{"waist":0.,"height":1.70,"volume":.060},{"waist":.31,"height":1.70,"volume":.061},False),
    )
    rows=[]
    for label,before,after,should_pass in cases:
        legacy=edit_gate(before,after,"legacy_or")
        candidate=edit_gate(before,after,"target_specific")
        rows.append({"fixture":label,"oracle_pass":should_pass,"legacy_pass":legacy,
                     "candidate_pass":candidate})
    old_false_passes=sum(r["legacy_pass"] and not r["oracle_pass"] for r in rows)
    strict_correct=all(r["candidate_pass"]==r["oracle_pass"] for r in rows)
    return {"schema":"scp.numerics.n02.v1",
        "verdict":"PASS_NARROW" if old_false_passes>=1 and strict_correct else "RED",
        "legacy_false_passes":old_false_passes,"target_specific_correct":strict_correct,
        "production_source_modified":False,"cases":rows}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--lane",choices=("n01","n02"),required=True)
    args=parser.parse_args()
    report=n01() if args.lane=="n01" else n02()
    report.update({"fixture_class":"ORIGINAL_SYNTHETIC_SCALARS_ONLY",
        "real_character_accepted":False,"mvp_accepted":False,"release_authorized":False,
        "code_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python":platform.python_version()})
    print(json.dumps(report,sort_keys=True,indent=2,allow_nan=False))
    if report["verdict"]!="PASS_NARROW":
        raise SystemExit(12)

if __name__=="__main__":
    main()
