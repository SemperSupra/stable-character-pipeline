"""R083 independent join witness for real CC0 garments plus 144-frame MPFB tissue animation.
Only original fictional actors; does not certify reference identity, shoe-floor contact, or tissue physics.
"""
import argparse,hashlib,json,math,struct,sys
from pathlib import Path
import bpy
def fail(code):
 print("R083_INTEGRATION_RED",code,flush=True)
 raise RuntimeError(code)
def digest(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def skin_digest(obj):
 bpy.context.view_layer.update()
 e=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
 m=e.to_mesh()
 try:
  h=hashlib.sha256()
  for v in m.vertices:h.update(struct.pack("<3f",v.co.x,v.co.y,v.co.z))
  return h.hexdigest(),len(m.vertices)
 finally:e.to_mesh_clear()
def parse():
 p=argparse.ArgumentParser()
 p.add_argument("--scene",required=True);p.add_argument("--sha",required=True)
 p.add_argument("--wardrobe",required=True);p.add_argument("--fine",required=True)
 p.add_argument("--out",required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])
def verify(a):
 scene=Path(a.scene)
 if digest(scene)!=a.sha:fail("INTEGRATED_BLEND_HASH_MISMATCH")
 base=json.loads(Path(a.wardrobe).read_text())
 fine=json.loads(Path(a.fine).read_text())
 if base["schema"]!="scp.r082.mpfb-cc0-native-outfit.v1":fail("WRONG_CLOTHING_SOURCE_SCHEMA")
 if fine["schema"]!="scp.r081.native-fine-motion.v1":fail("WRONG_TISSUE_SCHEMA")
 if fine["scene_sha256"]!=a.sha:fail("JOIN_FINE_SCENE_SHA_MISMATCH")
 sc=bpy.context.scene
 if sc.get("r082_wardrobe")!="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL" or sc.get("r081_tier")!="FICTIONAL_24FPS_PROVISIONAL_TISSUE":fail("DUAL_SOURCE_TIER_LOST")
 if (sc.frame_start,sc.frame_end,sc.render.fps)!=(0,143,24):fail("INTEGRATED_TIMEBASE_LOST")
 if len(base["characters"])!=2 or len(fine["actors"])!=2:fail("ACTOR_PAIR_COUNT_CHANGED")
 witness=[]
 for f in (0,47,95,143):
  sc.frame_set(f);actors=[]
  for i,row in enumerate(base["characters"]):
   name=row["name"]
   if name!=fine["actors"][i]["name"]:fail("ACTOR_SOURCE_ORDER_MISMATCH")
   body=bpy.data.objects.get(name+"_MPFBBody")
   rig=bpy.data.objects.get(name+"_MPFBRig")
   root=bpy.data.objects.get(name+"_MotionRoot")
   if not body or not rig or not root or len(rig.data.bones)!=163:fail("ACTOR_RIG_MISSING")
   if len(row["garments"])!=3:fail("MISSING_OUTFIT_LAYER")
   if not any(md.type=="ARMATURE" and md.object==rig for md in body.modifiers):fail("BODY_BINDING_LOST")
   keys=body.data.shape_keys
   if not keys:fail("TISSUE_KEYS_LOST")
   for part in ("chest","abdomen","hip"):
    for sign in ("positive","negative"):
     if "R081_"+part+"_"+sign not in keys.key_blocks:fail("TISSUE_SIGNED_KEY_MISSING")
   hb,n=skin_digest(body)
   raw=len(body.data.vertices)
   if raw<19000 or not (100<=n<=raw):fail("SKIN_GEOMETRY_OR_ORIGINAL_TOPOLOGY_LOST")
   outfits=[]
   for garment in row["garments"]:
    obj=bpy.data.objects.get(garment["native_object"])
    if not obj or not any(md.type=="ARMATURE" and md.object==rig for md in obj.modifiers):fail("GARMENT_SKIN_BINDING_LOST_"+garment["asset"])
    hg,n=skin_digest(obj)
    if n!=garment["evaluated_vertices"]:fail("GARMENT_VERTEX_COUNT_CHANGED_"+garment["asset"])
    outfits.append({"asset":garment["asset"],"sha256":hg})
   actors.append({"name":name,"root_x":round(root.location.x,6),
                  "body_sha256":hb,"garment_vertex_sha256":outfits,
                  "active_tissue_channels":sum(1 for k in keys.key_blocks if k.name.startswith("R081_") and abs(k.value)>1e-8)})
  witness.append({"frame":f,"actors":actors})
 for i in (0,1):
  b0=witness[0]["actors"][i];b1=witness[1]["actors"][i]
  if b0["body_sha256"]==b1["body_sha256"]:fail("BODY_ANIMATION_STATIC")
  if not abs(b1["root_x"]-b0["root_x"])>.5:fail("ROOT_NOT_MOVING")
  if not any(w["actors"][i]["active_tissue_channels"] for w in witness):fail("TISSUE_NOT_DRIVEN")
  for j in range(3):
   if b0["garment_vertex_sha256"][j]["sha256"]==b1["garment_vertex_sha256"][j]["sha256"]:fail("GARMENT_NOT_MOVING_"+str(j))
 result={"schema":"scp.r083.dressed-fine-native-join.v1","integrated_scene_sha256":a.sha,
         "wardrobe_source_scene_sha256":base["blend_sha256"],"source_baseline_sha256":base["source_baseline_sha256"],
         "frames":144,"fps":24,"status":"PASS_NATIVE_SKIN_GARMENT_TISSUE_TIMELINE_NARROW",
         "witness":witness,"both_original_fictional":True,
         "real_identity_accepted":False,"reference_outfit_accepted":False,"true_contact_accepted":False,
         "cloth_dynamics_accepted":False,"real_tissue_physics_accepted":False,"photoreal_accepted":False,
         "mvp_accepted":False,"release_authorized":False}
 path=Path(a.out)/"integrated.json"
 path.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
 print("R083_INTEGRATED_PASS_NARROW",json.dumps({"sha":a.sha,"frames":144,"actors":[x["name"] for x in witness[0]["actors"]],"garments_per_actor":3},sort_keys=True))
if __name__=="__main__":
 try:verify(parse())
 except (OSError,ValueError,TypeError,KeyError,RuntimeError) as exc:
  print("R083_FAIL_CLOSED",repr(exc),file=sys.stderr);sys.exit(12)
