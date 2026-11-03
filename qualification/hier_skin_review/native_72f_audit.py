#!/usr/bin/env python3
"""Read-only independent native Blender R009 source-safe skin/hierarchy oracle.
Source test envelopes are NOT biological or species-specific ROM.
"""
import bpy,sys,json,math,pathlib,runpy
args=sys.argv[sys.argv.index("--")+1:]
if len(args)!=5:raise SystemExit("source original_native original_receipt review_receipt fault")
src,original,original_receipt,out,fault=map(str,args)
spec=json.loads(pathlib.Path(src).read_text())
if spec["source_class"]!="ORIGINAL_SELF_AUTHORED_SYNTHETIC":raise SystemExit("SOURCE_NOT_ADMITTED")
saved=list(sys.argv)
sys.argv=["blender","--",src,original_receipt]
try:runpy.run_path(original,run_name="__main__")
finally:sys.argv=saved
if fault=="knee_rotation":
 bpy.context.scene.frame_set(36)
 arm=bpy.data.objects["SyntheticLeft"]
 pb=arm.pose.bones["shin"]
 pb.rotation_euler[0]+=0.4
 pb.keyframe_insert(data_path="rotation_euler",frame=36)
elif fault=="skin_denominator":
 ob=bpy.data.objects["SyntheticLeft_blended"]
 ob.vertex_groups["shin"].add([2],0.0,"REPLACE")
elif fault=="false_science":
 spec["physical_human_ROM"]="PASS"
elif fault!="baseline":raise SystemExit("UNSUPPORTED_FAULT")
def reject(reason):raise ValueError("NATIVE_RIG_REJECT:"+reason)
try:
 if spec["physical_human_ROM"]!="UNKNOWN" or spec["private_R009"]!="HELD_NOT_ACCEPTED":reject("FALSE_HUMAN_SCIENCE_PROMOTION")
 if len(spec["frames"])!=72 or spec["fps"]!=12:reject("CLOCK_OR_FRAME_COUNT")
 maxang=maxgap=maxdelta=0.
 for actor in spec["actor_ids"]:
  arm=bpy.data.objects[actor];ob=bpy.data.objects[actor+"_blended"]
  if arm.data.bones["shin"].parent!=arm.data.bones["thigh"] or arm.data.bones["foot"].parent!=arm.data.bones["shin"]:
   reject("UNPARENTED_JOINT")
  if sum(mod.type=="ARMATURE" and mod.object==arm for mod in ob.modifiers)!=1:
   reject("ACTUAL_SKIN_MODIFIER_MISSING")
  for vertex in ob.data.vertices:
   vals=[g.weight for g in vertex.groups]
   if abs(sum(vals)-1)>1e-6:reject("SOURCE_VERTEX_WEIGHT_DENOMINATOR")
   if vertex.index in (2,3) and (len(vals)!=2 or min(vals)<.1 or max(vals)>.9):
    reject("MISSING_DUAL_INFLUENCE")
  for f,row in enumerate(spec["frames"]):
   if row["frame"]!=f:reject("SOURCE_FRAME_INDEX")
   bpy.context.scene.frame_set(f)
   bpy.context.view_layer.update()
   hip=arm.pose.bones["thigh"];knee=arm.pose.bones["shin"];foot=arm.pose.bones["foot"]
   ae=max(abs(hip.rotation_euler[0]-math.radians(row["hip_deg"])),
          abs(knee.rotation_euler[0]-math.radians(row["knee_deg"])))
   maxang=max(maxang,ae)
   if ae>2e-5:reject("SOURCE_ANGLE_TO_BPY_FK_MISMATCH")
   gap=max((knee.head-hip.tail).length,(foot.head-knee.tail).length)
   maxgap=max(maxgap,gap)
   if gap>2e-5:reject("PARENT_CHAIN_DISCONTINUITY")
   delta=max(abs((hip.tail-hip.head).length-.5),abs((knee.tail-knee.head).length-.48))
   maxdelta=max(maxdelta,delta)
   if delta>2e-5:reject("HIERARCHY_SEGMENT_LENGTH_DRIFT")
 result={"schema":"scp.r009.independent-native-72f-skin-hierarchy.v1",
 "status":"PASS_ORIGINAL_SYNTHETIC_NATIVE_72F_FK_AND_SKIN_ONLY",
 "actors":len(spec["actor_ids"]),"frame_count":len(spec["frames"]),
 "max_angle_radians_error":maxang,"max_parent_joint_gap_m":maxgap,
 "max_limb_length_error_m":maxdelta,
 "fixture_rom_only":spec["fixture_envelope_only"],
 "real_biological_rom":"UNKNOWN","measured_ground_contact":"UNKNOWN",
 "protected_R009":"HELD_NOT_ACCEPTED"}
 with pathlib.Path(out).open("x") as f:json.dump(result,f,sort_keys=True,indent=2);f.write("\n")
 print(json.dumps(result,sort_keys=True))
except ValueError as exc:
 print(str(exc),file=sys.stderr)
 sys.exit(2)
