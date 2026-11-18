#!/usr/bin/env python3
"""R091 public synthetic-only morphology, wardrobe, and soft-tissue falsifiers."""
import argparse
import json
import math
from pathlib import Path

P=Path(__file__).with_name("synthetic_contract.json")

def finite(v):
    return isinstance(v,(float,int)) and not isinstance(v,bool) and math.isfinite(v)

def morphology(ref, observed, tol):
    if not ref or len(ref)!=len(observed) or len(tol)!=len(ref) or not all(finite(x) for x in ref+observed+tol) or any(x<=0 for x in tol):
        return False
    return all(abs(a-b)<=t for a,b,t in zip(ref,observed,tol))

def wardrobe(rights, penetration, slide, collisions, contact, max_p=.003, max_s=.05):
    return (rights=="CC0-explicit-file" and all(finite(v) for v in (penetration,slide,max_p,max_s))
            and 0<=penetration<=max_p and 0<=slide<=max_s
            and isinstance(collisions,int) and not isinstance(collisions,bool) and collisions==0
            and contact is True)

def tissue(samples, rate):
    if not isinstance(rate,int) or isinstance(rate,bool) or rate<48 or rate>1000 or len(samples)<3 or not all(finite(v) for v in samples):
        return False
    # Numeric sanity only, not biomechanical calibration.
    return max(abs(v) for v in samples)<.05 and abs(samples[-1])<=abs(samples[1])

def run(lane):
    data=json.loads(P.read_text(encoding="utf-8"))
    assert data["scope"]=="original-synthetic-controls-only"
    if lane=="morphology":
        x=data["identity"]["morphology_landmarks_m"];t=data["identity"]["tolerances_m"]
        assert morphology(x,[a+.001 for a in x],t)
        assert not morphology(x,[x[0]+.03,*x[1:]],t), "critical landmark must not be averaged away"
        assert not morphology(x,[x[0],float("nan"),x[2]],t)
        assert not morphology(x,x,[0,*t[1:]])
    elif lane=="wardrobe":
        w=data["wardrobe"]
        assert wardrobe(w["rights"],w["ground_penetration_m"],w["planted_slide_m_s"],w["collision_count"],w["has_contact"])
        assert not wardrobe("AGPL3",0,0,0,True)
        assert not wardrobe("CC0-explicit-file",.07216,0,0,True), "R084 bootie penetration RED must remain RED"
        assert not wardrobe("CC0-explicit-file",0,1.138464,0,True), "R084 skate RED must remain RED"
        assert not wardrobe("CC0-explicit-file",0,0,0,False)
        assert not wardrobe("CC0-explicit-file",float("nan"),0,0,True)
    elif lane=="tissue":
        t=data["tissue"]
        assert tissue(t["displacements_m"],t["sample_rate_hz"])
        assert not tissue([0,.001,float("nan")],240)
        assert not tissue([0,.1,.1],240)
        assert not tissue([0,.01,.02],240)
        assert not tissue([0,.001,.0002],0)
        assert t["calibrated"] is False, "synthetic oscillator must never claim biomechanics"
    else:
        raise ValueError(lane)
    print(json.dumps({"lane":lane,"outcome":"PASS_SOURCE_ONLY","source":"original-synthetic-controls","native_geometry":"NOT_TESTED","identity":"HOLD","realism":"HOLD"},sort_keys=True))

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--lane",choices=("morphology","wardrobe","tissue"),required=True)
    run(p.parse_args().lane)
