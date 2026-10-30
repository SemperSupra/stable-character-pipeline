"""ROM-V1 offline, source-original URDF parser/adapter candidate.

This is NOT a robotics safety controller and cannot qualify arbitrary URDF files.
Only local source files, no networking, imports or untrusted side effects.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

MAX_XML=1024*1024
MAX_JOINTS=64

def finite(value):
    number=float(value)
    if not math.isfinite(number):
        raise ValueError("NONFINITE_JOINT_PARAMETER")
    return number

def read_model(raw):
    if not 0<len(raw)<=MAX_XML or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("UNADMITTED_URDF_XML")
    root=ET.fromstring(raw)
    if root.tag!="robot" or not root.get("name"):
        raise ValueError("ROBOT_ROOT_REQUIRED")
    links=[x.get("name") for x in root.findall("link")]
    if len(links)<2 or len(links)>128 or len(set(links))!=len(links) or any(not x for x in links):
        raise ValueError("UNQUALIFIED_LINK_SET")
    nodes=root.findall("joint")
    if len(nodes)<1 or len(nodes)>MAX_JOINTS:
        raise ValueError("UNQUALIFIED_JOINT_COUNT")
    joints={}
    for el in nodes:
        name,kind=el.get("name"),el.get("type")
        if not name or name in joints or kind not in ("fixed","revolute","prismatic","continuous"):
            raise ValueError("JOINT_NAME_KIND_UNSUPPORTED")
        par,ch=el.find("parent"),el.find("child")
        p,c=par.get("link") if par is not None else None,ch.get("link") if ch is not None else None
        if not p or not c or p not in links or c not in links or p==c:
            raise ValueError("JOINT_PARENT_CHILD_INVALID")
        entry={"name":name,"kind":kind,"parent":p,"child":c,
               "units":"m" if kind=="prismatic" else "rad" if kind!="fixed" else "none",
               "status":"PROPOSED_ORIGINAL_SOURCE_NOT_SAFETY_QUALIFIED"}
        if kind!="fixed":
            axis=el.find("axis")
            data=(axis.get("xyz") if axis is not None else "1 0 0")
            values=[finite(v) for v in data.split()]
            if len(values)!=3 or sum(x*x for x in values)<1e-12:
                raise ValueError("INVALID_AXIS")
            entry["source_axis_xyz"]=values
            limit=el.find("limit")
            if limit is None:
                raise ValueError("NO_ACTUATOR_LIMIT")
            v=limit.attrib
            for required in ("velocity","effort"):
                if required not in v or finite(v[required])<=0:
                    raise ValueError("INVALID_VELOCITY_EFFORT")
            entry["max_velocity"]=finite(v["velocity"])
            entry["max_effort"]=finite(v["effort"])
            if kind!="continuous":
                if "lower" not in v or "upper" not in v:
                    raise ValueError("MISSING_HARD_RANGE")
                lo,hi=finite(v["lower"]),finite(v["upper"])
                if lo>=hi:
                    raise ValueError("INVALID_HARD_RANGE")
                entry["hard_min"],entry["hard_max"]=lo,hi
            elif "lower" in v or "upper" in v:
                raise ValueError("CONTINUOUS_HAS_POSITION_LIMIT")
        mimic=el.find("mimic")
        if mimic is not None:
            if mimic.get("joint") is None:
                raise ValueError("MIMIC_DEPENDENCY_MISSING")
            entry["mimic"]={"master":mimic.get("joint"),
                            "multiplier":finite(mimic.get("multiplier","1")),
                            "offset":finite(mimic.get("offset","0"))}
        joints[name]=entry
    if len(set(j["child"] for j in joints.values()))!=len(joints):
        raise ValueError("KINEMATIC_TREE_CHILD_DUPLICATION")
    for name,j in joints.items():
        if "mimic" not in j:
            continue
        master=j["mimic"]["master"]
        if master not in joints or master==name or joints[master]["units"]!=j["units"]:
            raise ValueError("MIMIC_SOURCE_OR_UNIT_INVALID")
        seen={name}
        while master in joints and "mimic" in joints[master]:
            if master in seen:
                raise ValueError("MIMIC_CYCLE")
            seen.add(master);master=joints[master]["mimic"]["master"]
        if master in seen:
            raise ValueError("MIMIC_CYCLE")
    # This only validates source model syntax; loop closure, geometry, native controller
    # authority, and actual observed actuator/force measurements are still unknown.
    return {"schema":"scp.rom.urdf_source_candidate.v1",
            "rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
            "status":"PROPOSED_MECHANISM_LIMITS_UNQUALIFIED",
            "source_sha256":hashlib.sha256(raw).hexdigest(),
            "robot":root.get("name"),"joints":[joints[n] for n in sorted(joints)],
            "unverified":["actual_hardware_revision","measured_joint_motion",
                          "acceleration","jerk","actual_effort","collisions","thermal",
                          "transmission","loop_closure","controller_and_license_rights"]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--urdf",required=True);p.add_argument("--out",required=True)
    args=p.parse_args()
    path=Path(args.urdf)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_XML:
        raise ValueError("URDF_SOURCE_NOT_ADMITTED")
    receipt=read_model(path.read_bytes())
    output=Path(args.out)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"status":receipt["status"],"source_sha256":receipt["source_sha256"],
                      "joint_count":len(receipt["joints"])}))
if __name__=="__main__":
    main()
