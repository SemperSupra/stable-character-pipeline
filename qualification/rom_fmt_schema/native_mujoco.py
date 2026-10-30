"""W4C: actual native MuJoCo MJCF admission, source-clean fictional hinge.

No real motor, muscle or physical safety acceptance. A finite simulation solver
responding to limits is not permission to release robotic hardware.
"""
import hashlib
import json
import math
from pathlib import Path
import mujoco
from export_projection import fixture,inspect_source_projection

def model_xml(lo=-0.75,hi=0.75,limited=True):
    flag="true" if limited else "false"
    return f'''<mujoco model="OriginalSyntheticHinge">
      <compiler angle="radian" autolimits="true"/>
      <option gravity="0 0 0" timestep="0.002"/>
      <worldbody>
        <body name="Base" pos="0 0 0">
          <body name="Link" pos="0 0 0">
            <joint name="OriginalHinge" type="hinge" axis="1 0 0"
                   range="{lo} {hi}" limited="{flag}" damping="0.1"/>
            <geom name="LinkGeom" type="capsule" fromto="0 0 0 0 0 0.5"
                  size="0.05" mass="1"/>
          </body>
        </body>
      </worldbody>
    </mujoco>'''

def inspect(xml,expected=(-.75,.75),must_limit=True):
    model=mujoco.MjModel.from_xml_string(xml)
    j=model.joint("OriginalHinge")
    jid=j.id
    if int(model.jnt_type[jid])!=int(mujoco.mjtJoint.mjJNT_HINGE):
        raise ValueError("NATIVE_HINGE_KIND")
    bounds=[float(x) for x in model.jnt_range[jid]]
    if any(abs(x-y)>1e-9 for x,y in zip(bounds,expected)):
        raise ValueError("NATIVE_MJCF_JOINT_LIMIT_CHANGED")
    if bool(model.jnt_limited[jid])!=must_limit:
        raise ValueError("NATIVE_MJCF_LIMIT_FLAG")
    return model,bounds

def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    xml=model_xml()
    model,bounds=inspect(xml)
    data=mujoco.MjData(model)
    mujoco.mj_forward(model,data)
    rest_q=float(data.qpos[0])
    if abs(rest_q)>1e-10:
        raise ValueError("NATIVE_INITIAL_POSE_NOT_ZERO")
    data.qpos[0]=.9
    mujoco.mj_forward(model,data)
    # Out of range qpos is STILL present until constraint dynamics act.
    # In particular MJCF does not form a hard source-level 'pose clamp'.
    observed_outside=float(data.qpos[0])
    if not math.isclose(observed_outside,.9,abs_tol=1e-9):
        raise ValueError("UNEXPECTED_NATIVE_QPOS_CLAMP")
    model_limit_constraint_count=int(data.nefc)
    if model_limit_constraint_count<=0:
        raise ValueError("NATIVE_JOINT_LIMIT_DID_NOT_GENERATE_CONSTRAINT")
    # Negative model: same limits as strings but disabled solver behavior;
    # this MUST NOT be counted as enforceable constraints.
    unsafe_xml=model_xml(limited=False)
    unsafe_model,_=inspect(unsafe_xml,must_limit=False)
    bad_data=mujoco.MjData(unsafe_model)
    bad_data.qpos[0]=.9
    mujoco.mj_forward(unsafe_model,bad_data)
    if int(bad_data.nefc)!=0:
        raise ValueError("UNLIMITED_MODEL_CONSTRAINT_NEGATIVE_INCORRECT")
    # Different limit numerics must be detected, not silently accepted.
    try:
        inspect(model_xml(hi=1.5))
    except ValueError as e:
        if str(e)!="NATIVE_MJCF_JOINT_LIMIT_CHANGED":raise
    else:
        raise ValueError("MUTATED_LIMIT_FALSE_PASS")
    source=fixture()
    source["hard_min"]=-.75;source["hard_max"]=.75
    proposal=inspect_source_projection(source)
    if proposal["status"]!="SOURCE_TEXT_PROJECTION_TEST_ONLY_NOT_NATIVE_ENGINE":
        raise ValueError("SOURCE_PROJECTION_NOT_QUALIFIED")
    report={"schema":"scp.rom.w4c_native_mujoco.v1",
            "status":"PASS_NATIVE_FICTIONAL_HINGE_LIMIT_OBSERVED",
            "mujoco_version":getattr(mujoco,"__version__","unknown"),
            "source_mjcf_sha256":hashlib.sha256(xml.encode()).hexdigest(),
            "source_joint":"OriginalHinge","source_position_bounds_rad":bounds,
            "initial_qpos_rad":rest_q,
            "out_of_bounds_qpos_after_forward_rad":observed_outside,
            "joint_limit_solver_constraints":model_limit_constraint_count,
            "disabled_limit_solver_constraints":int(bad_data.nefc),
            "modified_source_limit":"REJECTED",
            "mechanical_hardware_safety":"UNKNOWN_NOT_PHYSICAL_HARDWARE",
            "motor_velocity_effort_thermal":"UNKNOWN_NO_ACTUATOR",
            "biological_anatomy":"UNKNOWN_NOT_MODELLED"}
    (out/"synthetic_hinge.mjcf").write_text(xml)
    (out/"mujoco_observation.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("ROM_W4C_NATIVE_MUJOCO",json.dumps(report,sort_keys=True))
    return report
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    run(p.parse_args().out)
