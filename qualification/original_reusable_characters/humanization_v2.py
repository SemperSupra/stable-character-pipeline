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
             (1.19, 1.12), (1.30, 1.22), (1.38, 1),
             (1.42, .57), (1.475, .44)]
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


def loft_anatomy(g, material, rings, bone_at_y, sides=32):
    """One skin-weighted continuous ring mesh, outward triangles and sloped normals.

    rings are (height_m, center_z_m, width_radius_m, depth_radius_m).
    Parent source bones are never edited; this is a geometric skin variant only.
    """
    part = g.part(material)
    start = len(part["p"]) // 3
    assert len(rings) >= 3 and all(r[2] > 0 and r[3] > 0 for r in rings)
    assert all(rings[k][0] < rings[k+1][0] for k in range(len(rings)-1))
    for k, (y, cz, rx, rz) in enumerate(rings):
        prev = rings[max(0, k-1)]
        nxt = rings[min(len(rings)-1, k+1)]
        dy = nxt[0] - prev[0]
        drx = (nxt[2] - prev[2]) / dy
        drz = (nxt[3] - prev[3]) / dy
        dcz = (nxt[1] - prev[1]) / dy
        a, b, blend = bone_at_y(y)
        assert a in v1.JIDX and b in v1.JIDX and 0 <= blend <= 1
        for j in range(sides):
            phi = 2 * math.pi * j / sides
            co, si = math.cos(phi), math.sin(phi)
            part["p"].extend([rx * co, y, cz + rz * si])
            normal = v1.unit((rz * co,
                    -(drx * rz * co * co + rx * drz * si * si + rx * dcz * si),
                    rx * si))
            part["n"].extend(normal)
            part["j"].extend([v1.JIDX[a], v1.JIDX[b], 0, 0])
            part["w"].extend([blend, 1 - blend, 0, 0])
    for k in range(len(rings) - 1):
        for j in range(sides):
            a = start + k * sides + j
            b = start + k * sides + (j + 1) % sides
            part["i"].extend([a, a + sides, b, b, a + sides, b + sides])


def head_and_neck(g, skin, hair, male):
    """Continuous anatomical jaw/neck/scalp; no floating head or hair ellipsoid."""
    # The coat collar reaches 1.475m, leaving ~4.5cm visible neck.
    rings = [
        (1.405, 0, .062, .060),
        (1.448, 0, .056, .056),
        (1.480, -.003, .052, .054),
        (1.500, -.008, .053, .054),
        (1.519, -.013, .060, .060),
        (1.548, -.013, .072, .072),
        (1.574, -.010, .081, .083),
        (1.611, 0, .091 if male else .088, .095),
        (1.657, 0, .102 if male else .096, .105),
        (1.701, .008, .102 if male else .097, .106),
        (1.737, .019, .085, .093),
        (1.766, .025, .052, .062),
        (1.785, .028, .005, .010),
    ]
    def w(y):
        t = max(0., min(1., (1.553 - y) / .083))
        return ("neck", "head", t)
    loft_anatomy(g, skin, rings, w, sides=36)
    # Hair forms a thin source-original scalp shell, not a hovering sphere.
    scalp = [(1.716, .009, .104 if male else .100, .109),
             (1.740, .020, .090, .098),
             (1.766, .025, .056, .068),
             (1.787, .029, .008, .013)]
    loft_anatomy(g, hair, scalp, lambda _: ("head", "head", 1.), sides=36)


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
    # Jointed skinned head/neck and scalp are now one anatomical surface each.
    head_and_neck(g, skin, hair, male)
    E(skin, (0,1.635,-.108), (.016,.033,.028), "head")
    E(skin, (0,1.604,-.126), (.019,.011,.014), "head")
    E(skin, (0,1.585,-.097), (.031,.007,.007), "head")
    for s in (-1,1):
        E(skin,(s*.100,1.65,.011),(.019,.032,.017),"head")
        E("eyeWhite",(s*.041,1.666,-.102),(.019,.012,.007),"head",10,14)
        E("iris",(s*.041,1.665,-.109),(.009,.009,.004),"head",10,14)
        E(hair,(s*.042,1.691,-.105),(.027,.006,.005),"head",8,14)
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
        # Narrow sleeve starts inside continuous chest, avoiding ball-joint cap.
        sleeve_start = (s*.203, 1.345, 0.)
        g.tube(coat,sleeve_start,el,.075,.050,
               f"shoulder_{side}",f"elbow_{side}",steps=20,sides=24)
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
