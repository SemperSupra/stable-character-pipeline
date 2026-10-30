"""W6-B5B: actual six-deform-bone native rest basis witness, ORIGINAL proxy only.

Do not conflate B5 four-bone source matrices with NEW C5A/W5D six-bone
rest, do not infer anatomy/ROM/physical joint limits from rest matrices.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"walk_w16c5a"))
from native_sole import add_actor,ACTORS,LEGS,SOURCE
EXPECTED={"Upper":(0.,0.,1.08,0.,0.,.48),
          "Lower":(0.,0.,.48,0.,0.,-.12),
          "Foot":(0.,0.,-.12,0.,.18,-.12)}
def flatten(m):return [float(m[i][j]) for i in range(4) for j in range(4)]
def run(source_raw,profile,out):
 s=json.loads(source_raw)
 if s.get("schema")!="scp.walk_c4_original_ground_feasibility.v1" or s.get("rights")!=SOURCE or s.get("profile")!=profile or s.get("rest_hip_height")!=1.08 or s.get("bone_lengths")!=[.6,.6] or s.get("fps_num")!=12 or s.get("fps_den")!=1:
  raise ValueError("W6B5B_SOURCE_RIGHTS_CLOCK_REST")
 bpy.ops.wm.read_factory_settings(use_empty=True)
 all_actor=[]
 for ai,(name,x) in enumerate(ACTORS):
  if len(s.get("actors",[]))!=2 or s["actors"][ai]["id"]!=name:
   raise ValueError("W6B5B_ACTOR_ORIGIN")
  arm,obj,landmarks=add_actor(name,x)
  if len(arm.pose.bones)!=6 or len(obj.vertex_groups)!=6:
   raise ValueError("W6B5B_BONE_COUNT")
  bones=[]
  for leg,sign in LEGS:
   for part in ("Upper","Lower","Foot"):
    b=arm.data.bones[leg+part]
    par=b.parent
    expected_parent="" if part=="Upper" else leg+("Upper" if part=="Lower" else "Lower")
    if (par.name if par else "")!=expected_parent:raise ValueError("W6B5B_PARENT")
    h=Vector((sign*.22,)+EXPECTED[part][0:3][1:])
    # Expected source bone head/tail are in ARMATURE-local coordinates:
    head=Vector((sign*.22,EXPECTED[part][2],EXPECTED[part][3])) if False else None
    if part=="Upper":
     eh=(sign*.22,0.,1.08);et=(sign*.22,0.,.48)
    elif part=="Lower":
     eh=(sign*.22,0.,.48);et=(sign*.22,0.,-.12)
    else:
     eh=(sign*.22,0.,-.12);et=(sign*.22,.18,-.12)
    if max(abs(float(b.head_local[i])-eh[i]) for i in range(3))>1e-6 or max(abs(float(b.tail_local[i])-et[i]) for i in range(3))>1e-6:
     raise ValueError("W6B5B_ACTUAL_NATIVE_REST_ENDPOINT")
    m=b.matrix_local
    local=par.matrix_local.inverted()@m if par else m
    if abs(m.to_3x3().determinant()-1)>1e-6:
     raise ValueError("W6B5B_NATIVE_REST_DET")
    axis=(b.tail_local-b.head_local).normalized()
    expected_axis=Vector((0.,1.,0.)) if part=="Foot" else Vector((0.,0.,-1.))
    if (axis-expected_axis).length>1e-6:
     raise ValueError("W6B5B_SOURCE_REST_AXIS")
    bones.append({"id":leg+part,"parent":expected_parent,
      "expected_head":list(eh),"expected_tail":list(et),
      "world_rest_matrix_rowmajor":flatten(m),"parent_local_rest_rowmajor":flatten(local),
      "source_axis":list(expected_axis),"native_det":float(m.to_3x3().determinant())})
  all_actor.append({"actor":name,"bones":bones,"weights":len(obj.vertex_groups),
    "foot_landmark_ids":landmarks})
  bpy.data.objects.remove(obj,do_unlink=True)
  bpy.data.objects.remove(arm,do_unlink=True)
 out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
 r={"schema":"scp.walk_w6b5b_native_sixbone_rest.v1",
 "status":"PASS_NATIVE_SOURCE_ORIGINAL_SIX_BONE_REST_ONLY",
 "source_rights":SOURCE,"source_sha256":hashlib.sha256(source_raw).hexdigest(),
 "source_profile":profile,"source_clock":"12/1_SYNTHETIC_ZERO",
 "actors":all_actor,"native_deform_bones_per_actor":6,
 "knee_rom":"UNKNOWN_NO_INDIVIDUAL_OR_SPECIES_JCS_LIMITS",
 "scope":"TRUE_BLENDER_REST_PARENT_SIXBONE_NOT_DERIVED_FROM_B5_FOURBONE_TRANSLATIONS"}
 out.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
 print("W6B5B_NATIVE_SIX_BONE_REST_PASS",profile,len(all_actor))
if __name__=="__main__":
 a=argparse.ArgumentParser();a.add_argument("--source",required=True)
 a.add_argument("--profile",choices=("forward","outward"),required=True)
 a.add_argument("--out",required=True);x=a.parse_args()
 run(Path(x.source).read_bytes(),x.profile,x.out)
