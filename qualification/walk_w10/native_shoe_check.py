"""W10 independent actual native Blender shoe-contact qualification.
Read back saved W09 editable .blend instead of trusting the original keying
function or the source-only W08 IK receipt. Original procedural 2D units only.
"""
import argparse,hashlib,json,math
from pathlib import Path
import bpy

def verify(scene_json,blend_path,perturb=False):
    original=Path(scene_json).read_bytes()
    model=json.loads(original)
    if model.get("schema")!="scp.walk_motion.v1" or model.get("source_rights")!="ORIGINAL_PROGRAMMATIC_PROCEDURAL_ONLY":
        raise ValueError("NATIVE_SOURCE_RIGHTS_OR_SCHEMA")
    if len(model["frames"])!=72 or model.get("fps")!=12:
        raise ValueError("NATIVE_CLOCK")
    bpy.ops.wm.open_mainfile(filepath=str(Path(blend_path).resolve()))
    scene=bpy.context.scene
    if scene.frame_start!=0 or scene.frame_end!=71 or scene.render.fps!=12:
        raise ValueError("NATIVE_BLEND_TIMELINE_MISMATCH")
    witness=[]
    maximum_center_residual=0.
    maximum_stance_slip=0.
    minimum_native_sole=math.inf
    previous={}
    mutated=False
    for frame in model["frames"]:
        i=frame["index"]
        if i!=len(witness):raise ValueError("NATIVE_SOURCE_FRAME_INDEX")
        scene.frame_set(i)
        deps=bpy.context.evaluated_depsgraph_get()
        observations={}
        for actor in model["actors"]:
            aid=actor["id"];p=frame["actors"][aid]
            facing=actor["facing"]
            observed={}
            for side in ("left","right"):
                name=aid+"_foot_"+side
                native=bpy.data.objects.get(name)
                if native is None or native.type!="MESH":
                    raise ValueError("NATIVE_SHOE_MISSING")
                if perturb and not mutated and i==0 and aid==model["actors"][0]["id"] and side=="left":
                    native.location.x+=.06
                    bpy.context.view_layer.update()
                    mutated=True
                    deps=bpy.context.evaluated_depsgraph_get()
                ev=native.evaluated_get(deps)
                x=float(ev.matrix_world.translation.x)
                y=float(ev.matrix_world.translation.y)
                ankle=p["joints"]["ankle_"+side]
                expected_x=ankle[0]+facing*.07
                expected_y=ankle[1]-.03
                center_error=math.hypot(x-expected_x,y-expected_y)
                maximum_center_residual=max(maximum_center_residual,center_error)
                if center_error>1e-5:
                    raise ValueError("NATIVE_SHOE_SOURCE_DRIFT")
                mesh=ev.to_mesh()
                if mesh is None or not mesh.vertices:raise ValueError("NATIVE_SHOE_EMPTY_MESH")
                try:
                    sole=min(float((ev.matrix_world@v.co).y) for v in mesh.vertices)
                finally:
                    ev.to_mesh_clear()
                minimum_native_sole=min(minimum_native_sole,sole)
                if sole< -0.005:raise ValueError("NATIVE_SHOE_GROUND_PENETRATION")
                stance=bool(p["contact"][side])
                if stance:
                    if sole>.032:raise ValueError("NATIVE_STANCE_SHOE_HOVERS")
                    key=(aid,side)
                    if key in previous and previous[key][0]:
                        slip=math.hypot(x-previous[key][1],y-previous[key][2])
                        maximum_stance_slip=max(maximum_stance_slip,slip)
                        if slip>1e-6:raise ValueError("NATIVE_SHOE_STANCE_SKATE")
                    previous[key]=(True,x,y)
                else:
                    previous[(aid,side)]=(False,x,y)
                observed[side]={"planted":stance,"center_x":round(x,9),
                                "center_y":round(y,9),"minimum_mesh_y":round(sole,9)}
            observations[aid]=observed
        witness.append({"frame":i,"source_timestamp_ms":frame["timestamp_ms"],"feet":observations})
    if perturb and not mutated:raise ValueError("NATIVE_NEGATIVE_CONTROL_NOT_INJECTED")
    return {"schema":"scp.walk_w10_native_shoe_witness.v1",
            "status":"PASS_INDEPENDENT_BPY_SHOE_CONTACT_SOURCE_AND_GEOMETRY",
            "source_sha256":hashlib.sha256(original).hexdigest(),
            "blend_sha256":hashlib.sha256(Path(blend_path).read_bytes()).hexdigest(),
            "frames":72,"shoe_observations":288,
            "maximum_native_center_residual":maximum_center_residual,
            "maximum_native_stance_slip":maximum_stance_slip,
            "minimum_native_shoe_mesh_y":minimum_native_sole,
            "ground_y":0.,"ground_unit":"ORIGINAL_UNCALIBRATED_SOURCE_XY",
            "scope":"ORIGINAL_OBJECT_PART_AVATARS_NO_WEIGHTED_SKIN_NO_PRIVATE_PEOPLE",
            "per_frame_evaluated_native_shoes":witness}

def main():
    args=argparse.ArgumentParser()
    args.add_argument("--source",required=True)
    args.add_argument("--blend",required=True)
    args.add_argument("--out",required=True)
    p=args.parse_args()
    good=verify(p.source,p.blend)
    try:
        verify(p.source,p.blend,perturb=True)
    except ValueError as e:
        if str(e)!="NATIVE_SHOE_SOURCE_DRIFT":raise
        good["adversarial_native_shoe_060_shift"]="REJECTED_AS_EXPECTED"
    else:
        raise ValueError("INVALID_FALSE_PASS_NATIVE_SHOE_ADVERSARIAL")
    Path(p.out).write_text(json.dumps(good,sort_keys=True,indent=2)+"\n")
    print("W10_INDEPENDENT_NATIVE_SHOE_CONTACT_PASS",
          json.dumps({k:v for k,v in good.items() if k!="per_frame_evaluated_native_shoes"},sort_keys=True))
if __name__=="__main__":main()
