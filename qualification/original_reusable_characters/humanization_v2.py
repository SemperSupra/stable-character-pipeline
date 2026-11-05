#!/usr/bin/env python3
"""Original-only humanized geometry variant; v1 source and rig remain unchanged.

This is a procedural mesh research candidate, not human/ROM/gait acceptance.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path

source = Path(__file__).with_name("generate_original_glb.py")
spec = importlib.util.spec_from_file_location("original_r009", source)
v1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v1)


def torso(g, mat, widths):
    """Single lofted torso rather than independent intersecting ellipsoids."""
    p = g.part(mat)
    base = len(p["p"]) // 3
    rings = [(0.84, .95), (.92, 1), (1.01, .84), (1.09, .88),
             (1.19, 1.12), (1.30, 1.22), (1.38, 1), (1.42, .52)]
    n = 32
    for y, factor in rings:
        lo, hi, t = (("pelvis", "spine", max(0, min(1, (1.11-y)/.18)))
                     if y <= 1.11 else
                     ("spine", "chest", max(0, min(1, (1.38-y)/.27))))
        rx = widths[0] * factor
        rz = widths[1] * (.92 if y > 1.38 else 1)
        for j in range(n):
            ang = 2 * math.pi * j / n
            cs, sn = math.cos(ang), math.sin(ang)
            p["p"].extend([rx*cs, y, rz*sn])
            p["n"].extend(v1.unit((cs/rx, 0, sn/rz)))
            p["j"].extend([v1.JIDX[lo], v1.JIDX[hi], 0, 0])
            p["w"].extend([t, 1-t, 0, 0])
    for k in range(len(rings)-1):
        for j in range(n):
            a = base + k*n + j
            b = base + k*n + (j+1)%n
            p["i"].extend([a,a+n,b,b,a+n,b+n])


def make_figure(which):
    g = v1.Geometry()
    male = which == 0
    skin = "skinWarm" if male else "skinCool"
    hair = "ebonyHair" if male else "chestnutHair"
    coat = "coralJacket" if male else "tealJacket"
    pants = "slatePants" if male else "ochrePants"
    shoe = "darkBoots" if male else "earthBoots"
    torso(g, coat, (.183 if male else .168, .117 if male else .126))
    E = g.ellipsoid
    E(pants,(0,.845,.005),(.192 if male else .198,.135,.128),"pelvis",14,24)
    # ~0.26m-high anatomical head on a ~1.8m figure, with facial landmarks.
    g.tube(skin,(0,1.406,0),(0,1.598,0),.061,.055,"neck","head",steps=16,sides=24)
    E(skin, (0,1.655,0), (.101 if male else .094,.131,.108), "head",20,28)
    E(skin, (0,1.596,-.020), (.076,.067,.082), "head")
    E(skin, (0,1.640,-.108), (.017,.038,.029), "head")
    E(skin, (0,1.604,-.127), (.022,.012,.015), "head")
    E(skin, (0,1.584,-.100), (.038,.008,.009), "head")
    for s in (-1,1):
        E(skin,(s*.100,1.65,.011),(.019,.032,.017),"head")
        E("eyeWhite",(s*.041,1.666,-.102),(.019,.012,.007),"head",10,14)
        E("iris",(s*.041,1.665,-.109),(.009,.009,.004),"head",10,14)
        E(hair,(s*.042,1.691,-.105),(.027,.006,.005),"head",8,14)
    E(hair,(0,1.752,.016),(.101,.061,.114),"head",16,24)
    if male:
        E("scarf",(0,1.47,-.065),(.104,.034,.063),"neck")
    else:
        for s in (-1,1):
            E(hair,(s*.086,1.56,.035),(.030,.176,.078),"head")
        E(hair,(0,1.545,.093),(.080,.185,.071),"head")
    for s in (-1,1):
        side = "L" if s == -1 else "R"
        h,k,a = [v1.POS[f"{role}_{side}"] for role in ("hip","knee","ankle")]
        g.tube(pants,h,k,.113 if male else .120,.082,
               f"hip_{side}",f"knee_{side}",steps=18,sides=22)
        g.tube(pants,k,a,.084,.060,
               f"knee_{side}",f"ankle_{side}",steps=18,sides=22)
        E(pants,(s*.14,.34,.006),(.077,.108,.074),f"knee_{side}")
        E(shoe,(s*.14,.07,-.007),(.076,.062,.078),f"ankle_{side}")
        E(shoe,(s*.14,.05,-.102),(.083,.044,.110),f"ankle_{side}")
        sh,el,wr = [v1.POS[f"{role}_{side}"]
                     for role in ("shoulder","elbow","wrist")]
        E(coat,(s*.218,1.337,0),(.086,.096,.080),f"shoulder_{side}",12,18)
        g.tube(coat,sh,el,.083,.057,f"shoulder_{side}",f"elbow_{side}",18,22)
        g.tube(coat,el,wr,.059,.041,f"elbow_{side}",f"wrist_{side}",18,22)
        E(skin,(wr[0],wr[1]-.04,wr[2]),(.043,.063,.025),f"wrist_{side}")
        for j, length in enumerate((.045,.065,.070,.060,.047)):
            E(skin,(wr[0]+(j-2)*.018,wr[1]-.087-length*.3,wr[2]),
              (.009,length*.51,.010),f"wrist_{side}",10,12)
    for part in g.parts.values():
        xyz = part["p"]
        old, good = part["i"], []
        for t in range(0,len(old),3):
            ia,ib,ic = old[t:t+3]
            u=[xyz[ib*3+x]-xyz[ia*3+x] for x in range(3)]
            v=[xyz[ic*3+x]-xyz[ia*3+x] for x in range(3)]
            cross=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],
                   u[0]*v[1]-u[1]*v[0])
            if sum(x*x for x in cross)>1e-16:
                good.extend((ia,ib,ic))
        part["i"]=good
    return g


def generate(out):
    original = v1.figure_geometry
    try:
        v1.figure_geometry = make_figure
        receipt = v1.make_demo(out)
    finally:
        v1.figure_geometry = original
    receipt["variant"]="original_humanization_v2_research"
    receipt["functional_joints_per_person"]=17
    receipt["toe_joints"]=0
    receipt["facial_blendshapes"]=0
    receipt["human_motion_accepted"]=False
    return receipt


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",required=True)
    parser.add_argument("--receipt",required=True)
    args=parser.parse_args()
    result=generate(args.out)
    Path(args.receipt).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))
