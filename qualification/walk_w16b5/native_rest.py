"""W16-B5 native Blender bone-rest matrix bridge, original source-only.

B4 authored 4x4 ROWMAJOR translation-only source/world frames. They are NOT
Blender rest basis matrices. Observe true native .matrix_local before mapping.
"""
import argparse,json,math
from pathlib import Path
import bpy
from mathutils import Vector
RIGHTS="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
def row(m):return [float(m[i][j]) for i in range(4) for j in range(4)]
def check(profile,source):
 if source.get("schema")!="scp.walk_dual_leg_rest_clock.v4" or source.get("rights")!=RIGHTS or source.get("profile")!=profile:
  raise ValueError("B5_SOURCE_OR_RIGHTS")
 if source.get("basis")!="BLENDER_RH_Z_UP_SOURCE" or source.get("fps")!="12/1":
  raise ValueError("B5_SOURCE_FRAME")
 bpy.ops.wm.read_factory_settings(use_empty=True)
 out=[]
 for ai,actor in enumerate(source["actors"]):
  if actor["id"]!=("CobaltOriginal","MarigoldOriginal")[ai]:
   raise ValueError("B5_ACTOR_ORDER")
  arm_data=bpy.data.armatures.new(actor["id"]+"_B5Data")
  arm=bpy.data.objects.new(actor["id"]+"_B5",arm_data)
  bpy.context.scene.collection.objects.link(arm)
  bpy.context.view_layer.objects.active=arm;arm.select_set(True)
  bpy.ops.object.mode_set(mode="EDIT")
  named={}
  for b in actor["rest_bones"]:
   if b["id"] not in ("LeftUpper","LeftLower","RightUpper","RightLower"):
    raise ValueError("B5_BONE_ID")
   b0=arm_data.edit_bones.new(b["id"])
   b0.head=tuple(b["rest_head"]);b0.tail=tuple(b["rest_tail"])
   named[b["id"]]=b0
  for b in actor["rest_bones"]:
   if b["parent"]:
    named[b["id"]].parent=named[b["parent"]]
    named[b["id"]].use_connect=True
  bpy.ops.object.mode_set(mode="OBJECT")
  if len(arm.data.bones)!=4:raise ValueError("B5_BONE_COUNT")
  obs=[]
  for b in actor["rest_bones"]:
   bone=arm.data.bones[b["id"]]
   par=arm.data.bones[b["parent"]] if b["parent"] else None
   h=tuple(float(x) for x in bone.head_local)
   t=tuple(float(x) for x in bone.tail_local)
   if max(abs(h[j]-b["rest_head"][j]) for j in range(3))>1e-6:
    raise ValueError("B5_NATIVE_REST_HEAD")
   if max(abs(t[j]-b["rest_tail"][j]) for j in range(3))>1e-6:
    raise ValueError("B5_NATIVE_REST_TAIL")
   local=par.matrix_local.inverted()@bone.matrix_local if par else bone.matrix_local
   x=bone.matrix_local
   if max(abs(float(x[j][3])-h[j]) for j in range(3))>1e-6:
    raise ValueError("B5_NATIVE_MATRIX_TRANSLATION")
   determinant=float(x.to_3x3().determinant())
   if abs(determinant-1)>1e-6:
    raise ValueError("B5_NATIVE_REST_ROTATION_DETERMINANT")
   obs.append({"id":b["id"],"parent":b["parent"],"head":h,"tail":t,
    "source_translation_only_rowmajor":b["world_rest_bind_rowmajor"],
    "source_parent_translation_only_rowmajor":b["parent_local_rest_bind_rowmajor"],
    "native_world_rest_rowmajor":row(x),
    "native_parent_local_rest_rowmajor":row(local),
    "native_det":determinant,
    "source_matrix_equals_actual_native":max(abs(row(x)[i]-b["world_rest_bind_rowmajor"][i]) for i in range(16))<1e-6})
  out.append({"actor_id":actor["id"],"bones":obs})
  bpy.data.objects.remove(arm,do_unlink=True)
 source_eq_count=sum(int(b["source_matrix_equals_actual_native"]) for a in out for b in a["bones"])
 if source_eq_count==8:
  raise ValueError("B5_UNEXPECTED_SAME_BASIS_ADAPTER_NEEDED")
 return {"schema":"scp.walk_w16b5_native_rest_bridge.v1","status":"PASS_OBSERVED_NATIVE_BONE_REST_WITH_EXPLICIT_BASIS_DIFFERENCE",
  "source_rights":RIGHTS,"source_schema":source["schema"],"profile":profile,
  "actors":out,"native_equals_B4_translation_only_count":source_eq_count,
  "admission_scope":"REST_BRIDGE_ONLY_NO_C5_GROUNDED_NATIVE_OR_PRIVATE_HUMAN"}
def main():
 p=argparse.ArgumentParser();p.add_argument("--source",required=True)
 p.add_argument("--profile",choices=("forward","outward"),required=True);p.add_argument("--out",required=True)
 a=p.parse_args();q=json.loads(Path(a.source).read_text())
 r=check(a.profile,q);Path(a.out).write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
 print("W16B5_NATIVE_REST_BASIS_BRIDGE_PASS",r["profile"],r["native_equals_B4_translation_only_count"])
if __name__=="__main__":main()
