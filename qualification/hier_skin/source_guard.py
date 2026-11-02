#!/usr/bin/env python3
"""Self-authored fixture specification. ROM numbers are test envelopes, never human clinical norms."""
import argparse,hashlib,json,math,pathlib,sys
SCHEMA="scp.r009.public-hierarchical-skin.v1"
ACTORS=["SyntheticLeft","SyntheticRight"]
def generate():
    frames=[]
    for f in range(72):
        angle=2*math.pi*f/24
        frames.append({"frame":f,"hip_deg":round(25*math.sin(angle),8),
                       "knee_deg":round(45+20*(1-math.cos(angle)),8)})
    return {"schema":SCHEMA,"source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
            "fps":12,"frames":frames,"actor_ids":ACTORS,
            "fixture_envelope_only":{"hip_deg":[-35,35],"knee_deg":[0,125]},
            "skin_weights":{"upper":[1.0,0.0],"knee":[0.5,0.5],"lower":[0.0,1.0]},
            "segment_lengths_m":[0.50,0.48],
            "private_R009":"HELD_NOT_ACCEPTED","physical_human_ROM":"UNKNOWN",
            "real_contact_force":"UNKNOWN","measured_gait":"NOT_ADMITTED"}
def verify(src):
    if src.get("schema")!=SCHEMA or src.get("source_class")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC":
        raise ValueError("SOURCE_CLASS_NOT_ADMITTED")
    if src.get("private_R009")!="HELD_NOT_ACCEPTED" or src.get("physical_human_ROM")!="UNKNOWN":
        raise ValueError("SCIENTIFIC_FALSE_PROMOTION")
    if src.get("actor_ids")!=ACTORS or src.get("fps")!=12 or len(src.get("frames",[]))!=72:
        raise ValueError("SOURCE_CLOCK_ACTORS_INVALID")
    if src.get("segment_lengths_m")!=[.5,.48]:
        raise ValueError("SEGMENT_GEOMETRY_INVALID")
    if src.get("fixture_envelope_only")!={"hip_deg":[-35,35],"knee_deg":[0,125]}:
        raise ValueError("UNADMITTED_ROM_RANGE")
    weights=src.get("skin_weights",{})
    for key in ("upper","knee","lower"):
        pair=weights.get(key)
        if not isinstance(pair,list) or len(pair)!=2 or any(not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 or v>1 for v in pair) or abs(sum(pair)-1)>1e-9:
            raise ValueError("SKIN_WEIGHT_NOT_NORMALIZED:"+key)
    if not 0.1<=weights["knee"][0]<=0.9 or not 0.1<=weights["knee"][1]<=0.9:
        raise ValueError("NOT_MULTI_INFLUENCE_SKIN")
    for i,rec in enumerate(src["frames"]):
        if rec.get("frame")!=i:raise ValueError("WRONG_SOURCE_FRAME")
        hip=rec.get("hip_deg");knee=rec.get("knee_deg")
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (hip,knee)):
            raise ValueError("NONFINITE_ROM")
        if not -35<=hip<=35 or not 0<=knee<=125:raise ValueError("FIXTURE_JOINT_ENVELOPE_VIOLATION")
    return True
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out");p.add_argument("--fault",default="baseline",choices=("baseline","hyper_knee","hip_outside","bad_weights","false_human","short_clock","degenerate"))
    a=p.parse_args();src=generate()
    if a.fault=="hyper_knee":src["frames"][19]["knee_deg"]=151
    if a.fault=="hip_outside":src["frames"][28]["hip_deg"]=-51
    if a.fault=="bad_weights":src["skin_weights"]["knee"]=[1.0,.4]
    if a.fault=="false_human":src["physical_human_ROM"]="PASS"
    if a.fault=="short_clock":src["frames"].pop()
    if a.fault=="degenerate":src["segment_lengths_m"][1]=0
    try:verify(src)
    except (ValueError,KeyError,TypeError) as e:
        print("HIERARCHICAL_SOURCE_REJECTED:"+str(e),file=sys.stderr);sys.exit(2)
    data=json.dumps(src,sort_keys=True,separators=(",",":")).encode()+b"\n"
    if a.out:
        with pathlib.Path(a.out).open("xb") as f:f.write(data)
    print(json.dumps({"schema":"scp.r009.hier-skin.source-receipt.v1",
        "status":"PASS_SYNTHETIC_FIXTURE_ENVELOPE_ONLY",
        "sha256":hashlib.sha256(data).hexdigest(),"actors":2,"frames":72,
        "human_ROM":"UNKNOWN","private_R009":"HELD"},sort_keys=True))
if __name__=="__main__":main()
