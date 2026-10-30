"""ROMFMT C: bounded original-source format-specific projection, not native engine proof.

For human/animal physiological sources or unknown coordinate axes: fail to project.
Native USD/OSIM/MJCF model loading is future work. Export test-only fragments.
"""
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET

SCHEMA="scp.rom.scalar_export_fixture.v1"

def authorized(model):
    if model.get("schema")!=SCHEMA or model.get("rights")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC" or model.get("authority")!="SYNTHETIC_TEST_ONLY":
        raise ValueError("RIGHTS_OR_LIMIT_AUTHORITY")
    if model.get("rig")!="OriginalRobot" or model.get("parent")!="Base" or model.get("child")!="Link":
        raise ValueError("JOINT_TOPOLOGY")
    if model.get("joint")!="OriginalHinge" or model.get("kind")!="revolute" or model.get("unit")!="rad" or model.get("frame")!="PARENT_LOCAL_TEST_ONLY":
        raise ValueError("JOINT_KIND_UNIT_OR_FRAME")
    if model.get("axis")!=[1,0,0]:
        raise ValueError("AXIS_NOT_USD_CARDINAL")
    for field in ("hard_min","hard_max","max_velocity","max_effort"):
        v=model.get(field)
        if type(v) not in (float,int) or not math.isfinite(v):
            raise ValueError("NUMERIC_LIMIT_INVALID")
    if model["hard_min"]>=model["hard_max"] or model["max_velocity"]<=0 or model["max_effort"]<=0:
        raise ValueError("LIMITS_INVALID")
    return model

def manifest_sha(m):
    return hashlib.sha256(json.dumps(m,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def usd_fragment(m):
    authorized(m)
    # PhysicsRevoluteJoint angular bounds are degrees even though URDF uses radians.
    lo=math.degrees(m["hard_min"]);hi=math.degrees(m["hard_max"])
    return (f'#usda 1.0\n(\n  metersPerUnit = 1\n  upAxis = "Z"\n)\n'
            'def Xform "OriginalRobot" {\n'
            ' def Xform "Base" {}\n def Xform "Link" {}\n'
            ' def PhysicsRevoluteJoint "OriginalHinge" {\n'
            '  uniform token physics:axis = "X"\n'
            '  rel physics:body0 = </OriginalRobot/Base>\n'
            '  rel physics:body1 = </OriginalRobot/Link>\n'
            f'  float physics:lowerLimit = {lo:.12g}\n'
            f'  float physics:upperLimit = {hi:.12g}\n'
            ' }\n}\n')

def urdf(m):
    authorized(m)
    root=ET.Element("robot",name=m["rig"])
    ET.SubElement(root,"link",name=m["parent"])
    ET.SubElement(root,"link",name=m["child"])
    joint=ET.SubElement(root,"joint",name=m["joint"],type="revolute")
    ET.SubElement(joint,"parent",link=m["parent"])
    ET.SubElement(joint,"child",link=m["child"])
    ET.SubElement(joint,"axis",xyz="1 0 0")
    ET.SubElement(joint,"limit",lower=str(m["hard_min"]),upper=str(m["hard_max"]),
                  velocity=str(m["max_velocity"]),effort=str(m["max_effort"]))
    return ET.tostring(root,encoding="unicode")

def mjcf(m):
    authorized(m)
    root=ET.Element("mujoco",model=m["rig"])
    ET.SubElement(root,"compiler",angle="radian")
    world=ET.SubElement(root,"worldbody")
    base=ET.SubElement(world,"body",name=m["parent"])
    link=ET.SubElement(base,"body",name=m["child"])
    ET.SubElement(link,"joint",name=m["joint"],type="hinge",axis="1 0 0",limited="true",
                  range=f'{m["hard_min"]} {m["hard_max"]}')
    # No actuator. The source max_effort is NOT asserted to survive in MJCF.
    return ET.tostring(root,encoding="unicode")

def opensim_coordinate(m):
    authorized(m)
    # Coordinate alone, NOT a complete independently loadable .osim model.
    node=ET.Element("Coordinate",name=m["joint"])
    for tag,val in (("motion_type","rotational"),("range",f'{m["hard_min"]} {m["hard_max"]}'),
                    ("clamped","true"),("locked","false")):
        ET.SubElement(node,tag).text=val
    return ET.tostring(node,encoding="unicode")

def inspect_source_projection(m):
    authorized(m)
    native_units={"USD":"degrees","URDF":"radians","MJCF":"radians with explicit compiler","OpenSim":"radians"}
    usd=usd_fragment(m)
    usdbounds=re.findall(r'physics:(?:lowerLimit|upperLimit) = (-?[0-9.]+)',usd)
    if len(usdbounds)!=2 or not math.isclose(math.radians(float(usdbounds[0])),m["hard_min"],abs_tol=1e-11) or not math.isclose(math.radians(float(usdbounds[1])),m["hard_max"],abs_tol=1e-11):
        raise ValueError("USD_ANGLE_UNIT_CONVERSION")
    robot=ET.fromstring(urdf(m));ul=robot.find("./joint/limit")
    if not ul or not all(math.isclose(float(ul.get(k)),m[mk],abs_tol=1e-12) for k,mk in
                         (("lower","hard_min"),("upper","hard_max"),("velocity","max_velocity"),("effort","max_effort"))):
        raise ValueError("URDF_JOINT_LOSS")
    sim=ET.fromstring(mjcf(m));sj=sim.find("./worldbody/body/body/joint")
    if sj is None or sj.get("limited")!="true" or [float(x) for x in sj.get("range").split()]!=[m["hard_min"],m["hard_max"]]:
        raise ValueError("MJCF_POSITION_LOSS")
    osim=ET.fromstring(opensim_coordinate(m))
    if osim.findtext("clamped")!="true" or [float(x) for x in osim.findtext("range").split()]!=[m["hard_min"],m["hard_max"]]:
        raise ValueError("OPENSIM_LIMIT_LOSS")
    return {"schema":"scp.rom.format_projection.v1",
            "status":"SOURCE_TEXT_PROJECTION_TEST_ONLY_NOT_NATIVE_ENGINE",
            "manifest_sha256":manifest_sha(m),"angles_by_format":native_units,
            "source_joint_id":m["joint"],"source_position_bounds_rad":[m["hard_min"],m["hard_max"]],
            "survival":{"USD":"POSITION_ONLY_DEGREES_SOURCE_TEXT",
                        "URDF":"POSITION_VELOCITY_EFFORT_SOURCE_XML",
                        "MJCF":"POSITION_ONLY_EFFORT_UNMODELED",
                        "OpenSim":"POSITION_CLAMP_COORDINATE_FRAGMENT_ONLY"},
            "unverified":["native_file_parser","source_skeleton_bone_mapping",
                          "physics_vs_usdskel","roundtrip_dcc_export",
                          "actual_3d_biomechanical_joint_frames","runtime_enforcement",
                          "external_model_license","human_animal_rom"]}

def fixture():
    return {"schema":SCHEMA,"rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
            "authority":"SYNTHETIC_TEST_ONLY","rig":"OriginalRobot",
            "parent":"Base","child":"Link","joint":"OriginalHinge",
            "kind":"revolute","unit":"rad","frame":"PARENT_LOCAL_TEST_ONLY",
            "axis":[1,0,0],"hard_min":-1.0,"hard_max":1.0,
            "max_velocity":2.0,"max_effort":10.0}

if __name__=="__main__":
    print(json.dumps(inspect_source_projection(fixture()),indent=2,sort_keys=True))
