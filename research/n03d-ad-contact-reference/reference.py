"""N03D-AD analytic contact-first reference; original synthetic, NOT real footwear acceptance.

Explicit SWING/HEEL/FLAT/TOE/UNKNOWN labels, two segment planar inverse kinematics,
rigid foot heel+toe and independent oracle from exact posed world endpoints.
"""
import hashlib
import json
import math

LENGTHS=(.45,.45)
FOOT_LENGTH=.2
STATES=("SWING","HEEL","FLAT","TOE","UNKNOWN")
FOLLOW={"SWING":{"SWING","HEEL","UNKNOWN"}, "HEEL":{"HEEL","FLAT","UNKNOWN"},
        "FLAT":{"FLAT","TOE","UNKNOWN"}, "TOE":{"TOE","SWING","UNKNOWN"},
        "UNKNOWN":set(STATES)}

def require(ok, code):
    if not ok:
        raise ValueError(code)

def finite(*values):
    return all(type(x) in (int,float) and math.isfinite(x) for x in values)

def ik2(hip, ankle, thigh=.45,shin=.45):
    """Circle-intersection knee, positive sagittal forward bend pole; never stretch."""
    require(len(hip)==2 and len(ankle)==2 and finite(*(hip+ankle),thigh,shin),"NUMERIC")
    require(thigh>0 and shin>0,"BAD_SEGMENTS")
    dx=ankle[0]-hip[0];dy=ankle[1]-hip[1]
    d=math.hypot(dx,dy)
    require(abs(thigh-shin)+1e-8 < d < thigh+shin-1e-8,"UNREACHABLE")
    a=(thigh*thigh-shin*shin+d*d)/(2*d)
    h=math.sqrt(max(0,thigh*thigh-a*a))
    knee=(hip[0]+a*dx/d-h*dy/d,hip[1]+a*dy/d+h*dx/d)
    require(abs(math.dist(hip,knee)-thigh)<1e-8 and abs(math.dist(knee,ankle)-shin)<1e-8,"IK_LENGTH")
    return tuple(round(x,10) for x in knee)

def stance_point(state, phase, step=.65, foot=.2):
    require(state in STATES and finite(phase,step,foot) and 0<=phase<=1 and step>foot>0,"STANCE_PARAM")
    if state=="HEEL":
        theta=.25*(1-phase)
        heel=(0.,0.);toe=(foot*math.cos(theta),foot*math.sin(theta))
    elif state=="FLAT":
        heel=(0.,0.);toe=(foot,0.)
    elif state=="TOE":
        theta=-.25*phase
        toe=(foot,0.)
        heel=(foot-foot*math.cos(theta),-foot*math.sin(theta))
    elif state=="SWING":
        # 0..1 interpolates from toe-off heel point to the next foothold.
        begin=(foot-foot*math.cos(.25), foot*math.sin(.25))
        heel=(begin[0]+(step-begin[0])*phase,begin[1]+.12*math.sin(math.pi*phase))
        toe=(heel[0]+foot,heel[1])
    else:
        raise ValueError("UNKNOWN_HAS_NO_SYNTHETIC_TRUTH")
    return tuple(float(x) for x in heel),tuple(float(x) for x in toe)

def synthetic():
    rows=[]
    for i in range(60):
        if i<12:state="HEEL";phase=i/11
        elif i<24:state="FLAT";phase=(i-12)/11
        elif i<36:state="TOE";phase=(i-24)/11
        else:state="SWING";phase=(i-36)/23
        heel,toe=stance_point(state,phase)
        hip=(.05+.25*i/59,.75)
        knee=ik2(hip,heel)
        rows.append({"frame":i,"time_s":i/60,"state":state,"heel_xy_m":list(heel),
                     "toe_xy_m":list(toe),"hip_xy_m":list(hip),"knee_xy_m":list(knee)})
    return {"schema":"scp.n03d-ad.synthetic-contact-reference.v1","source_class":"ORIGINAL_SYNTHETIC",
            "source_sha256":hashlib.sha256(b"n03d-ad-60hz-generated-analytic-reference-v1").hexdigest(),
            "ground_y_m":0.0,"frame_rate_hz":60,"source_has_known_contact":True,
            "real_actor_or_shoe":False,"mvp_accepted":False,"rows":rows}

def assess(doc, gap=.002,slip=.08):
    require(doc.get("schema")=="scp.n03d-ad.synthetic-contact-reference.v1" and
            doc.get("source_class")=="ORIGINAL_SYNTHETIC" and doc.get("real_actor_or_shoe") is False
            and doc.get("mvp_accepted") is False and doc.get("source_has_known_contact") is True,
            "PROVENANCE_OR_FORGED_RELEASE")
    require(doc.get("frame_rate_hz")==60 and doc.get("ground_y_m")==0 and
            isinstance(doc.get("rows"),list) and len(doc["rows"])==60,"TIMELINE")
    require(finite(gap,slip) and 0<gap<.05 and 0<slip<=1,"THRESHOLD")
    reasons=[];previous=None
    summaries={"HEEL":[],"FLAT":[],"TOE":[],"SWING":[]}
    for i,row in enumerate(doc["rows"]):
        require(row.get("frame")==i and finite(row.get("time_s")) and abs(row["time_s"]-i/60)<1e-8,"CLOCK")
        s=row.get("state")
        require(s in STATES and s!="UNKNOWN","UNKNOWN_NO_GROUND_TRUTH")
        if previous is not None:require(s in FOLLOW[previous],"ILLEGAL_CONTACT_TRANSITION")
        previous=s
        pts={}
        for k in ("heel_xy_m","toe_xy_m","hip_xy_m","knee_xy_m"):
            v=row.get(k)
            require(isinstance(v,list) and len(v)==2 and finite(*v),"FINITE_GEOMETRY")
            pts[k]=v
        heel,toe,hip,knee=(pts[k] for k in ("heel_xy_m","toe_xy_m","hip_xy_m","knee_xy_m"))
        # Ground-contact geometric truth is independent of the stage label.
        if min(heel[1],toe[1]) < -gap:reasons.append("GROUND_PENETRATION")
        if abs(math.dist(heel,toe)-FOOT_LENGTH)>1e-5:reasons.append("RIGID_FOOT_LENGTH")
        if abs(math.dist(hip,knee)-LENGTHS[0])>1e-5 or abs(math.dist(knee,heel)-LENGTHS[1])>1e-5:
            reasons.append("LEG_LENGTH")
        if s=="HEEL" and abs(heel[1])>gap:reasons.append("HEEL_NOT_PLANTED")
        if s=="FLAT" and (abs(heel[1])>gap or abs(toe[1])>gap):reasons.append("FLAT_NOT_PLANTED")
        if s=="TOE" and abs(toe[1])>gap:reasons.append("TOE_NOT_PLANTED")
        summaries[s].append(i)
        if i and s==doc["rows"][i-1]["state"]:
            prev=doc["rows"][i-1]
            contact_labels={"HEEL":["heel_xy_m"],"FLAT":["heel_xy_m","toe_xy_m"],"TOE":["toe_xy_m"],"SWING":[]}
            for key in contact_labels[s]:
                # Detect uncontrolled sliding only in declared same-phase contact.
                if math.dist(prev[key],row[key])*60>slip:reasons.append("PERSISTENT_CONTACT_SLIDE")
    return {"schema":"scp.n03d-ad.independent-analytic-critic.v1",
            "reference_result":"PASS_NARROW" if not reasons else "FAIL",
            "violations":sorted(set(reasons)),
            "state_counts":{k:len(v) for k,v in summaries.items()},
            "mvp_accepted":False,"native_footwear_accepted":False}

if __name__=="__main__":
    result=assess(synthetic())
    print(json.dumps(result,sort_keys=True))
    if result["reference_result"]!="PASS_NARROW":raise SystemExit(12)
