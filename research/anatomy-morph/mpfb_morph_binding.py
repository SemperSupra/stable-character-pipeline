"""R036 native MPFB macro-morph + anatomical proxy re-registration probe.

The proxy organs are original ellipsoids, NOT anatomical truth. This checks
actual native shape/rig refit behavior and measures anchor drift, keeping
identity, topology and license boundaries explicit.
"""
import bpy
import argparse
import hashlib
import importlib
import json
import math
import os
import struct
import sys
from mathutils import Vector

def args():
 p=argparse.ArgumentParser()
 p.add_argument("--stage",choices=["probe","verify"],required=True)
 p.add_argument("--out",required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])

def fail(reason):
 print("R036_MORPH_FAIL",reason)
 raise RuntimeError(reason)

def digest(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()

def mesh(obj):
 bpy.context.view_layer.update()
 eo=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
 me=eo.to_mesh()
 try:
  pts=[eo.matrix_world@v.co for v in me.vertices]
  sha=hashlib.sha256()
  for p in pts:sha.update(struct.pack("<3f",*p))
  mins=[min(p[i] for p in pts) for i in range(3)]
  maxs=[max(p[i] for p in pts) for i in range(3)]
  centroid=[sum(p[i] for p in pts)/len(pts) for i in range(3)]
  return {"sha256":sha.hexdigest(),"vertex_count":len(pts),
   "bounds_m":[round(maxs[i]-mins[i],8) for i in range(3)],
   "centroid_m":[round(c,8) for c in centroid]}
 finally: eo.to_mesh_clear()

def scene():
 body=bpy.data.objects.get("R036_Official_MPFB_Human")
 rig=bpy.data.objects.get("R036_Official_MPFB_Rig")
 organs=[bpy.data.objects.get("R036_AnatomyProxy_Left"),bpy.data.objects.get("R036_AnatomyProxy_Right")]
 if body is None or rig is None or any(o is None for o in organs):
  fail("missing official MPFB body, rig or synthetic organ proxies")
 if not any(m.type=="ARMATURE" and m.object==rig for m in body.modifiers):
  fail("original MPFB body no longer bound to native rig")
 if rig.get("r036_test_bone") not in rig.pose.bones: fail("unknown native anchor bone")
 for organ in organs:
  if not any(m.type=="ARMATURE" and m.object==rig for m in organ.modifiers):
   fail("organ lost rig modifier")
 return body,rig,organs

def install_mpfb_services():
 import addon_utils
 package="bl_ext.user_default.mpfb"
 if not addon_utils.check(package)[1]:
  addon_utils.enable(package,default_set=False,persistent=False)
 if not addon_utils.check(package)[1]:fail("native MPFB extension unavailable")
 hs=importlib.import_module(package+".services.humanservice").HumanService
 ts=importlib.import_module(package+".services.targetservice").TargetService
 properties=importlib.import_module(package+".entities.objectproperties").HumanObjectProperties
 return hs,ts,properties

def state(body,rig,organs,tag):
 bpy.context.scene.frame_set(1)
 m=mesh(body)
 selected=rig.get("r036_test_bone")
 bone=rig.data.bones[selected]
 head=rig.matrix_world@bone.head_local
 tail=rig.matrix_world@bone.tail_local
 axis=tail-head
 length=axis.length
 if length<1e-6:fail("zero-length official MPFB anchor bone")
 out={"profile":tag,"body":m,"torso_bone":selected,
  "torso_bone_length_m":round(length,8),
  "torso_head_m":[round(x,8) for x in head],
  "organ_anchors":[]}
 for organ in organs:
  g=mesh(organ)
  center=Vector(g["centroid_m"])
  distance=(center-head).length
  out["organ_anchors"].append({"id":organ.name,
   "organ_centroid_m":g["centroid_m"],
   "distance_to_torso_bone_head_m":round(distance,8),
   "distance_in_bone_lengths":round(distance/length,8),
   "vertex_count":g["vertex_count"]})
 return out

def binding_frame(rig):
    bone=rig.data.bones[rig.get("r036_test_bone")]
    start=rig.matrix_world@bone.head_local
    end=rig.matrix_world@bone.tail_local
    direction=end-start
    length=direction.length
    if length<1e-6:fail("cannot register to a degenerate native bone")
    rot=Vector((0,0,1)).rotation_difference(direction.normalized())
    return start,rot,length

def bind_norm_offsets(rig,organs):
    start,rot,length=binding_frame(rig)
    result=[]
    for organ in organs:
        center=Vector(mesh(organ)["centroid_m"])
        result.append(rot.inverted()@(center-start)/length)
    return result,length

def rebind_anatomy_to_refitted_bone(rig,organs,normalized_offsets,source_bone_length):
    # A deterministic, strictly synthetic rest-space alignment rule.
    # This fits a canonical local attachment relative to current native bone
    # orientation/length; it does not fit a real organ to surrounding tissues.
    start,rot,length=binding_frame(rig)
    for organ,offset in zip(organs,normalized_offsets):
        scale=length/source_bone_length
        organ.scale=(scale,scale,scale)
        bpy.context.view_layer.update()
        expected=start+rot@(offset*length)
        actual=Vector(mesh(organ)["centroid_m"])
        correction=expected-actual
        organ.location+=rig.matrix_world.inverted().to_3x3()@correction
        bpy.context.view_layer.update()
        residual=(Vector(mesh(organ)["centroid_m"])-expected).length
        if residual>1e-4:fail("synthetic organ/bone rebind did not converge: "+str(residual))

def probe(out):
 body,rig,organs=scene()
 hs,ts,props=install_mpfb_services()
 # Original native state, then two distinct MakeHuman macro morphs.
 scenarios=[
  ("baseline",None),
  ("taller_lighter",{"height":.78,"weight":.26}),
  ("shorter_heavier",{"height":.22,"weight":.79})
 ]
 states=[]
 source_vertices=len(body.data.vertices)
 bpy.context.scene.frame_set(1)
 normalized_offsets,source_bone_length=bind_norm_offsets(rig,organs)
 for label,profile in scenarios:
  raw=None
  if profile is not None:
   for prop,value in profile.items():
    props.set_value(prop,value,entity_reference=body)
   ts.reapply_macro_details(body)
   hs.refit(body)
   raw=state(body,rig,organs,label+"_before_anatomy_rebind")
   rebind_anatomy_to_refitted_bone(rig,organs,normalized_offsets,source_bone_length)
  value=state(body,rig,organs,label)
  if len(body.data.vertices)!=source_vertices:
   fail("MPFB morph changed canonical surface topology")
  if profile:
   value["profile_inputs"]=profile
   value["before_rebinding_normalized_distances"]=[item["distance_in_bone_lengths"] for item in raw["organ_anchors"]]
   value["after_rebinding_normalized_distances"]=[item["distance_in_bone_lengths"] for item in value["organ_anchors"]]
  states.append(value)
 if len({s["body"]["sha256"] for s in states})!=len(states):
  fail("distinct macro morph values did not change actual evaluated body geometry")
 for item in states[1:]:
  for d in item["organ_anchors"]:
   expected=states[0]["organ_anchors"][0]["distance_in_bone_lengths"]
   if abs(d["distance_in_bone_lengths"]-expected)>1e-4:
    fail("normalized proxy/bone rest attachment drift after rebind")
 if len({tuple(s["body"]["bounds_m"]) for s in states})<2:
  fail("macro morph did not change measurable geometry bounds")
 for item in states:
  if len(item["organ_anchors"])!=2:fail("missing proxy anatomical anchors after refit")
  if not math.isfinite(item["torso_bone_length_m"]):fail("nonfinite refitted rig")
 # Detect concrete anchor error and report. No anatomical threshold exists yet.
 variations={}
 base=states[0]
 for item in states[1:]:
  deviations=[round(item["organ_anchors"][i]["distance_in_bone_lengths"]-base["organ_anchors"][i]["distance_in_bone_lengths"],8) for i in range(2)]
  variations[item["profile"]]={"normalized_proxy_anchor_shifts":deviations,
   "actual_anatomic_registration":"HOLD_UNVALIDATED_REFERENCE"}
 src=os.path.join(out,"mpfb-morphed-anatomy.blend")
 bpy.ops.wm.save_as_mainfile(filepath=src,check_existing=False)
 result={"schema":"scp.anatomy.mpfb_macro_refit.v1",
  "status":"PASS_NATIVE_MORPH_SMOKE_ONLY",
  "blender":bpy.app.version_string,
  "official_mpfb_rig_bones":len(rig.data.bones),
  "canonical_skin_topology_vertices":source_vertices,
  "profiles":states,
  "normalized_anchor_drift":variations,
  "saved_blend_sha256":digest(src),
  "anatomy_alignment_admitted":False,
  "limits":"macro refit + attached synthetic proxies not organ geometry or contact/physiology"}
 with open(os.path.join(out,"morph-receipt.json"),"w") as f:json.dump(result,f,sort_keys=True,indent=2)
 print("R036_MORPH_RECEIPT "+json.dumps(result,sort_keys=True,separators=(",",":")))

def verify(out):
 body,rig,organs=scene()
 m=mesh(body)
 if not os.path.isfile(os.path.join(out,"morph-receipt.json")):
  fail("missing independent original recorded receipt")
 with open(os.path.join(out,"morph-receipt.json")) as f:original=json.load(f)
 # MPFB raw canonical topology includes helper vertices. The evaluated
 # mesh is smaller because MPFB mask modifiers intentionally hide helpers.
 if len(rig.data.bones)<100 or len(body.data.vertices)!=original["canonical_skin_topology_vertices"]:
  fail("saved refit scene lost expected exact MPFB rig/topology")
 target=original["profiles"][-1]["body"]["sha256"]
 bpy.context.scene.frame_set(1)
 if m["sha256"]!=target:fail("reopened morph geometry does not match exact source receipt")
 print("R036_MORPH_VERIFY "+json.dumps({"status":"PASS_REOPEN_MORPH_NARROW",
  "body_sha256":m["sha256"],"bones":len(rig.data.bones),
  "organ_count":len(organs),"anatomy_registration":"HOLD"},sort_keys=True))

if __name__=="__main__":
 n=args()
 if n.stage=="probe":probe(n.out)
 else:verify(n.out)
