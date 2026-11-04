"""R009 source-original reusable IK/contact primitives (research, not native rig acceptance).

This is an explicit-target three-dimensional analytic two-segment solver and an
explicit stance/swing target planner. It NEVER guesses biological contact from
skeleton pose and NEVER labels a rendered or private human asset as accepted.
Blender rig rest-basis, source skin and pose transfer are not validated here.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite, pi, sin, sqrt
from typing import Sequence

EPS = 1.0e-9


def vec3(value, name="vector"):
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        raise ValueError("INVALID_" + name.upper())
    if any(type(v) not in (int, float) or not isfinite(v) for v in value):
        raise ValueError("INVALID_" + name.upper())
    return tuple(float(v) for v in value)


def add(a, b): return tuple(x + y for x, y in zip(a, b))
def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def mul(a, n): return tuple(x * n for x in a)
def dot(a, b): return sum(x*y for x, y in zip(a, b))
def norm(a): return sqrt(dot(a, a))


def solve_two_bone(origin, target, pole, proximal_length, distal_length):
    """Solve hip/elbow -> knee/elbow -> ankle/hand in WORLD metres.

    The pole is a WORLD point defining the bend half-plane, not a bone-local
    Euler axis. Unreachable targets and ambiguous pole vectors fail closed.
    Output is an unattested geometry witness, not an original Blender bone pose.
    """
    a, b, p = (vec3(x, key) for key, x in (("origin", origin), ("target", target), ("pole", pole)))
    if any(type(x) not in (int, float) or not isfinite(x) or x <= 0
           for x in (proximal_length, distal_length)):
        raise ValueError("INVALID_SEGMENT_LENGTHS")
    l1, l2 = float(proximal_length), float(distal_length)
    offset = sub(b, a)
    distance = norm(offset)
    if distance <= EPS:
        raise ValueError("COINCIDENT_CHAIN_ENDPOINTS")
    if distance > l1 + l2 + EPS or distance < abs(l1-l2)-EPS:
        raise ValueError("UNREACHABLE_CHAIN_TARGET")
    direction = mul(offset, 1.0/distance)
    pole_offset = sub(p, a)
    perpendicular = sub(pole_offset, mul(direction, dot(pole_offset, direction)))
    pole_mag = norm(perpendicular)
    if pole_mag <= EPS:
        raise ValueError("AMBIGUOUS_BEND_POLE")
    toward = mul(perpendicular, 1.0/pole_mag)
    along = (l1*l1 + distance*distance - l2*l2) / (2.0*distance)
    radius2 = l1*l1 - along*along
    if radius2 < -1e-7:
        raise ValueError("INCONSISTENT_CHAIN_GEOMETRY")
    joint = add(add(a, mul(direction, along)), mul(toward, sqrt(max(0.0, radius2))))
    if abs(norm(sub(joint,a))-l1)>1e-7 or abs(norm(sub(joint,b))-l2)>1e-7:
        raise RuntimeError("CHAIN_RESIDUAL_ERROR")
    return {"origin":a, "joint":joint, "target":b,
            "residual_m": max(abs(norm(sub(joint,a))-l1), abs(norm(sub(joint,b))-l2)),
            "native_bone_pose_verified":False, "skin_deformation_verified":False}


@dataclass(frozen=True)
class Stance:
    start: int
    end: int
    anchor: tuple[float, float, float]


def plan_foot_targets(frame_count, stance_bouts: Sequence[Stance], swing_height_m=0.06):
    """Generate explicit world-space stance lock and interpolated swing targets.

    A stance is deliberately supplied by a controller and is NOT inferred from
    a mesh height proxy. Each stance anchor is held invariant in x/y/z. Motion
    between consecutive stances uses a smoothstep horizontal transition and
    a zero-height/zero-vertical-velocity swing-lift envelope at both endpoints.
    Pre/post intervals stay at nearest anchor and are NOT marked as contact.
    """
    if type(frame_count) is not int or not 2 <= frame_count <= 100000:
        raise ValueError("INVALID_FRAME_COUNT")
    if type(swing_height_m) not in (int,float) or not isfinite(swing_height_m) or swing_height_m<0:
        raise ValueError("INVALID_SWING_HEIGHT")
    if not isinstance(stance_bouts,(list,tuple)) or not stance_bouts:
        raise ValueError("MISSING_STANCE_BOUTS")
    bouts = []
    for item in stance_bouts:
        if not isinstance(item,Stance) or type(item.start) is not int or type(item.end) is not int:
            raise ValueError("INVALID_STANCE_BOUT")
        if not 0<=item.start<=item.end<frame_count:
            raise ValueError("INVALID_STANCE_CLOCK")
        bouts.append(Stance(item.start,item.end,vec3(item.anchor,"stance_anchor")))
    if bouts != sorted(bouts,key=lambda s:s.start):
        raise ValueError("UNSORTED_STANCE_BOUTS")
    for left,right in zip(bouts,bouts[1:]):
        if right.start<=left.end+1:
            raise ValueError("NO_SWING_INTERVAL_BETWEEN_STANCES")
    out=[]
    for f in range(frame_count):
        bout=next((b for b in bouts if b.start<=f<=b.end),None)
        if bout is not None:
            target=bout.anchor; mode="STANCE"
        elif f < bouts[0].start:
            target=bouts[0].anchor; mode="PRE"
        elif f > bouts[-1].end:
            target=bouts[-1].anchor; mode="POST"
        else:
            # Find the immediately preceding and following declared stance anchor.
            left=max((b for b in bouts if b.end<f),key=lambda x:x.end)
            right=min((b for b in bouts if b.start>f),key=lambda x:x.start)
            u=(f-left.end)/(right.start-left.end)
            ease=u*u*(3.0-2.0*u)
            target=add(left.anchor,mul(sub(right.anchor,left.anchor),ease))
            lift=float(swing_height_m)*(sin(pi*u)**2)
            target=(target[0],target[1],target[2]+lift)
            mode="SWING"
        out.append({"frame":f,"target":target,"mode":mode,"contact_certified":False})
    return out


def audit_contact_kinematics(left,right,hip_left,hip_right,leg_lengths,pole_left,pole_right):
    """Cross-frame geometry gate; never self-assert Blender/biological acceptance."""
    if len(left)!=len(right) or len(left)!=len(hip_left) or len(left)!=len(hip_right):
        raise ValueError("MISALIGNED_MOTION_CLOCKS")
    if not len(left):raise ValueError("EMPTY_MOTION_CLOCK")
    if not isinstance(leg_lengths,(tuple,list)) or len(leg_lengths)!=2:
        raise ValueError("INVALID_LEG_LENGTHS")
    solved={"L":[],"R":[]}
    for i in range(len(left)):
        for side,frames,hips,pole in (("L",left,hip_left,pole_left),("R",right,hip_right,pole_right)):
            if frames[i].get("frame")!=i:
                raise ValueError("MISMATCHED_FRAME_IDS")
            witness=solve_two_bone(hips[i],frames[i]["target"],pole[i],*leg_lengths)
            solved[side].append({"frame":i,"mode":frames[i]["mode"],"joint":witness["joint"],
                                "residual_m":witness["residual_m"]})
    return {"schema":"scp.r009.portable_explicit_foot_contact_ik.v1",
            "frames":len(left),"by_side":solved,
            "contact_source":"EXPLICIT_SYNTHETIC_STANCE_TARGET_NOT_MEASURED",
            "native_80_bone_skin_verification":"NOT_RUN",
            "real_person_identity_and_rights":"OUT_OF_SCOPE",
            "mvp_accepted":False}
