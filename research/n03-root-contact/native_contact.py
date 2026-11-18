"""N03 native evaluated CC0 shoe *root-only* feasibility bakeoff.
Never saves or exports edited scene. R084 source inputs and original mesh unchanged.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"r084-shoe-contact"))
from native_shoe_contact import sole_sample, digest, height_ground, reject
from shoe_contact import quantify
from contact_policy import plan, root_velocity

def original_tracks(scene,shoe,rig):
 rows=[]
 for f in range(72):
  scene.frame_set(f)
  rows.append(sole_sample(shoe,rig))
 return rows

def experiment(scene,actor):
 name=actor["name"]
 if name not in ("AsterOriginal","JuniperOriginal"):reject("UNAUTHORIZED_PROXY")
 rig=bpy.data.objects.get(name+"_MPFBRig")
 root=bpy.data.objects.get(name+"_MotionRoot")
 shoe_rows=[g for g in actor["garments"] if g["pack"]=="shoes01"]
 if len(shoe_rows)!=1 or not root or not rig:reject("SOURCE_RIG_OR_SHOE_MISSING")
 shoe=bpy.data.objects.get(shoe_rows[0]["native_object"])
 if not shoe:reject("SOURCE_SHOE_MISSING")
 if not any(m.type=="ARMATURE" and m.object==rig for m in shoe.modifiers):reject("SHOE_NATIVE_ARMATURE_MISMATCH")
 baseline=original_tracks(scene,shoe,rig)
 proposal=plan(baseline)
 got=[]
 max_translation_residual=0.
 try:
  for f,frame in enumerate(proposal["frames"]):
   scene.frame_set(f)
   original=root.location.copy()
   dx,dy,dz=frame["root_offset_m"]
   root.location=(original.x+dx,original.y+dy,original.z+dz)
   bpy.context.view_layer.update()
   sample=sole_sample(shoe,rig)
   for side in ("x_negative","x_positive"):
    raw=baseline[f][side]
    corrected=sample[side]
    observed=[corrected["xy_m"][0]-raw["xy_m"][0],corrected["xy_m"][1]-raw["xy_m"][1],corrected["z_m"]-raw["z_m"]]
    error=math.dist(observed,[dx,dy,dz])
    max_translation_residual=max(max_translation_residual,error)
    if not math.isfinite(error) or error>.002:reject("ACTUAL_NATIVE_ROOT_OFFSET_NOT_RIGID")
   got.append(sample)
   root.location=original
   bpy.context.view_layer.update()
 finally:
  scene.frame_set(0)
 output={}
 for side in ("x_negative","x_positive"):
  output[side]={"baseline":quantify([a[side] for a in baseline],12),
                "root_only_candidate":quantify([a[side] for a in got],12)}
 return {"name":name,"foot_partitions":output,
         "max_root_vertical_lift_m":max(f["root_offset_m"][2] for f in proposal["frames"]),
         "max_root_xy_correction_m":max(math.hypot(*f["root_offset_m"][:2]) for f in proposal["frames"]),
         "max_root_offset_rate_m_per_s":root_velocity(proposal["frames"],12),
         "double_contact_root_only_conflict_lower_bound_m":proposal["max_simultaneous_contact_conflict_lower_bound_m"],
         "root_transform_vs_evaluated_geometry_max_residual_m":max_translation_residual,
         "post_correction_native_evaluated":True,"anatomical_left_right_verified":False}

def run(a):
 scene=bpy.context.scene
 if digest(a.scene)!=a.sha:reject("SCENE_SHA_MISMATCH")
 if scene.get("r078_source")!="ORIGINAL_FICTIONAL_MPFBCORE_CC0" or scene.get("r082_wardrobe")!="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL":reject("SOURCE_RIGHTS_MARKER_MISMATCH")
 if (scene.frame_start,scene.frame_end,scene.render.fps)!=(0,71,12):reject("SCENE_CLOCK_MISMATCH")
 ground=bpy.data.objects.get("R078_Original_FlatParkProxy")
 if ground is None or abs(height_ground(ground))>1e-4:reject("GROUND_MISSING")
 ward=json.loads(Path(a.wardrobe).read_text())
 if ward.get("schema")!="scp.r082.mpfb-cc0-native-outfit.v1" or ward.get("blend_sha256")!=a.sha:reject("PARENT_RECEIPT_MISMATCH")
 actors=[experiment(scene,x) for x in ward["characters"]]
 if sorted(x["name"] for x in actors)!=["AsterOriginal","JuniperOriginal"]:reject("ACTOR_SET_MISMATCH")
 report={"schema":"scp.n03.native-root-only-feasibility.v1",
         "source_scene_sha256":a.sha,"parent_r084_native_source":"STORED_SYNTHETIC_CC0_GROUND_OBSERVER",
         "scene_frames":72,"fps":12,"actors":actors,
         "status":"HOLD_ROOT_ONLY_NOT_CONTACT_CONSTRAINED_IK",
         "native_source_scene_modified":False,"pose_track_saved":False,
         "measured_post_correction_synthetic_geometry":True,
         "mvp_accepted":False,"contact_accepted":False,"release_authorized":False}
 dest=Path(a.out)
 dest.mkdir(parents=True,exist_ok=False)
 (dest/"n03-root-only.json").write_text(json.dumps(report,sort_keys=True,allow_nan=False,indent=2)+"\n")
 print("N03_NATIVE_RESULT",json.dumps(report,sort_keys=True,allow_nan=False))

if __name__=="__main__":
 p=argparse.ArgumentParser()
 for k in ("scene","sha","wardrobe","out"):p.add_argument("--"+k,required=True)
 try:run(p.parse_args(sys.argv[sys.argv.index("--")+1:]))
 except (RuntimeError,ValueError,TypeError,KeyError,OSError) as e:
  print("N03_NATIVE_FAIL_CLOSED",repr(e),file=sys.stderr)
  sys.exit(12)
