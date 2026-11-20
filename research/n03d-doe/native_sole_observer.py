"""N03D real native CC0 shoe-geometry read-only witness, on source-pinned R090 scene.
No rig/scene edits, no protected identities, no semantic side claims.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent.parent/"r090-dressed"))
sys.path.insert(0,str(Path(__file__).parent.parent/"n03c-native-ik"))
from measure import stable_sole_sample,sha
from ik_contract import chain,validate_parents

def fail(reason):raise RuntimeError(reason)
def xyz(v):return [float(v.x),float(v.y),float(v.z)]
def dist_xy(p,q):return math.hypot(p[0]-q[0],p[1]-q[1])
def main():
 p=argparse.ArgumentParser()
 for n in ("scene","sha","wardrobe","retarget","out"):p.add_argument("--"+n,required=True)
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 if sha(a.scene)!=a.sha:fail("SOURCE_SHA_MISMATCH")
 sc=bpy.context.scene
 if sc.get("r078_source")!="ORIGINAL_FICTIONAL_MPFBCORE_CC0" or sc.get("r082_wardrobe")!="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL":fail("SOURCE_RIGHTS_HOLD")
 if sc.render.fps!=12 or sc.frame_end<71:fail("CLOCK_INVALID")
 ward=json.loads(Path(a.wardrobe).read_text());rt=json.loads(Path(a.retarget).read_text())
 if ward.get("schema")!="scp.r082.mpfb-cc0-native-outfit.v1" or rt.get("schema")!="scp.r090.sixsecond-dressed-real-retarget.v1" or rt.get("candidate_blend_sha256")!=a.sha or rt.get("input_scene_sha256")!=ward.get("blend_sha256"):fail("LINEAGE_MISMATCH")
 rows=[]
 for actor in ward["characters"]:
  name=actor["name"]
  if name not in ("AsterOriginal","JuniperOriginal"):fail("NOT_SYNTHETIC_ACTOR")
  rig=bpy.data.objects.get(name+"_MPFBRig")
  shoes=[g for g in actor["garments"] if g["pack"]=="shoes01"]
  if rig is None or len(rig.data.bones)!=163 or len(shoes)!=1:fail("INVALID_NATIVE_ACTOR")
  shoe=bpy.data.objects.get(shoes[0]["native_object"])
  if not shoe or not any(m.type=="ARMATURE" and m.object==rig for m in shoe.modifiers):fail("NOT_NATIVE_SHOE")
  for side in ("L","R"):
   bones=chain(side)
   parents={bn:rig.data.bones[bn].parent.name if rig.data.bones[bn].parent else None for bn in bones}
   validate_parents(side,parents)
  for frame in range(12,19):
   sc.frame_set(frame);bpy.context.view_layer.update()
   sole=stable_sole_sample(shoe)
   feet={s:xyz(rig.matrix_world@rig.pose.bones[chain(s)[0]].tail) for s in ("L","R")}
   samples={k:{"point_z_m":float(v["z_m"]),"xy_m":list(v["xy_m"])} for k,v in sole.items()}
   keys=sorted(samples)
   # Do NOT assert anatomical correspondence: minimize assignment cost for two foot-tail sites.
   x=[samples[k]["xy_m"] for k in keys]
   c0=dist_xy(feet["L"],x[0])+dist_xy(feet["R"],x[1])
   c1=dist_xy(feet["L"],x[1])+dist_xy(feet["R"],x[0])
   mapping={"L":keys[0],"R":keys[1]} if c0<=c1 else {"L":keys[1],"R":keys[0]}
   rows.append({"frame":frame,"foot_tail_world_m":feet,"sole_points":samples,
    "nearest_assignment":mapping,"assignment_cost_margin_m":abs(c0-c1),
    "anatomical_mapping_verified":False})
  # Evaluate read-only measured frame-to-frame slip in each local component.
  slips={}
  for part in rows[-7]["sole_points"]:
   xy=[r["sole_points"][part]["xy_m"] for r in rows[-7:]]
   slips[part]=max(dist_xy(xy[i],xy[i-1])*12 for i in range(1,len(xy)))
  penetration=max(max(0,-v["point_z_m"]) for r in rows[-7:] for v in r["sole_points"].values())
  rows[-1]["actor_summary"]={"actor":name,"max_sole_penetration_m":penetration,"max_local_component_xy_speed_mps":slips,"contact_state_ground_truth":False}
 out={"schema":"scp.n03d.native-sole-observer.v1","source_scene_sha256":a.sha,"actor_frames":rows,
 "native_evaluated_mesh":True,"correction_applied":False,"stance_phase_verified":False,
 "heel_toe_anatomy_verified":False,"gait_accepted":False,"mvp_accepted":False}
 Path(a.out).write_text(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("N03D_NATIVE_SOLE_READONLY_PASS_NARROW",json.dumps({"rows":len(rows),"source":a.sha}),flush=True)
if __name__=="__main__":
 try:main()
 except (KeyError,TypeError,ValueError,RuntimeError,IndexError,OSError) as e:
  print("N03D_FAIL_CLOSED",repr(e),file=sys.stderr);sys.exit(12)
