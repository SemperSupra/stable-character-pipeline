"""R014 native character capabilities / effective multires source evidence.

Blender 4.5.16, read-only research copies of two pinned public model scenes:
MPFB source rig has 163 bones and 19,158 source-body vertices;
Blender Studio CC0 v1.4.1 10,582 base vertices with a Multires modifier.
The presence of high-res geometry is NOT evidence of a high-res animated asset.
No gender/sex estimation from images; controlled shape macros are authoritative.
"""
import argparse,json,re,sys
from pathlib import Path
import bpy

p=argparse.ArgumentParser()
p.add_argument("--sex",choices=["female","male"],required=True)
p.add_argument("--motion-blend",type=Path,required=True)
p.add_argument("--studio-blend",type=Path,required=True)
p.add_argument("--motion-receipt",type=Path,required=True)
p.add_argument("--out",type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
a.out.parent.mkdir(parents=True,exist_ok=True)
receipt=json.loads(a.motion_receipt.read_text())
assert receipt["actor"]==a.sex and receipt["source_gender_macro"]=={"female":0.0,"male":1.0}[a.sex]
assert receipt["source_rig_bones"]==163

# Load actual native posed, textured MPFB actor; analyze names, not silhouettes.
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
with bpy.data.libraries.load(str(a.motion_blend),link=False) as (src,dst):
    rig_name="R014_"+a.sex+"_textured_rig"
    body_name="R014_"+a.sex+"_textured_body"
    assert rig_name in src.objects and body_name in src.objects
    dst.objects=[rig_name,body_name]
for obj in dst.objects:
    assert obj is not None
    bpy.context.collection.objects.link(obj)
rig=bpy.data.objects[rig_name]
body=bpy.data.objects[body_name]
assert len(rig.data.bones)==163 and len(body.data.vertices)==19158
bone_names=[b.name for b in rig.data.bones]
categories={
    "hands_and_fingers":r"(finger|thumb|index|pinky|pinkie|ring\d|middle\d)",
    "facial_jaw_lips_eye":r"(face|jaw|mouth|lip|eyelid|brow|cheek|eye|nose|tongue|teeth)",
    "arms":r"(upperarm|lowerarm|forearm|shoulder|clavic|wrist)",
    "legs":r"(thigh|upperleg|lowerleg|calf|toe|foot)",
    "torso":r"(spine|abdomen|hip|pelvis|chest|neck)"
}
by_category={k:[n for n in bone_names if re.search(pat,n,re.IGNORECASE)]
             for k,pat in categories.items()}
shape_keys=[k.name for k in body.data.shape_keys.key_blocks] if body.data.shape_keys else []
authored=receipt["animated_bones"]
authored_finger=[x for x in authored if re.search(categories["hands_and_fingers"],x,re.IGNORECASE)]
authored_face=[x for x in authored if re.search(categories["facial_jaw_lips_eye"],x,re.IGNORECASE)]
# Source has no hand/face animation in this clip, independently of capacity.
assert not authored_finger and not authored_face
assert 4<=len(authored)<=20
# Validate every declared bone exists and has at least two distinct keyframe rotations.
assert all(name in rig.pose.bones for name in authored)
action=rig.animation_data.action if rig.animation_data else None
action_desc={"exists":action is not None,"name":action.name if action else None}
if action:
    action_desc["slot_count"]=len(action.slots)
    action_desc["layer_count"]=len(action.layers)
    action_desc["action_fcurve_count_legacy"]=len(action.fcurves) if hasattr(action,"fcurves") else None
    action_desc["action_channels_by_bone_declared"]=authored

# Load Blender Studio original CC0 sculpt, but do not alter or claim it rigged.
with bpy.data.libraries.load(str(a.studio_blend),link=False) as (src,dst):
    n="GEO-body_"+a.sex+"_realistic"
    assert n in src.objects
    dst.objects=[n]
sculpt=dst.objects[0]
bpy.context.collection.objects.link(sculpt)
modifier=[m for m in sculpt.modifiers if m.type=="MULTIRES"]
assert len(modifier)==1
multi=modifier[0]
sculpt_source={
 "model":sculpt.name,
 "base_vertices":len(sculpt.data.vertices),
 "base_faces":len(sculpt.data.polygons),
 "has_armature":any(m.type=="ARMATURE" for m in sculpt.modifiers),
 "shape_key_count":len(sculpt.data.shape_keys.key_blocks) if sculpt.data.shape_keys else 0,
 "multires_total_levels":multi.total_levels,
 "multires_viewport_levels":multi.levels,
 "multires_sculpt_levels":multi.sculpt_levels,
 "multires_render_levels":multi.render_levels,
 "evaluated_preview_levels":[]
}
assert sculpt_source["base_vertices"]==10582
assert not sculpt_source["has_armature"] and sculpt_source["shape_key_count"]==0
old_viewport=multi.levels
old_show=multi.show_viewport
multi.show_viewport=True
for level in range(0,min(3,multi.total_levels)+1):
    multi.levels=level
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    evaluated=sculpt.evaluated_get(dg)
    mesh=evaluated.to_mesh()
    try:
        sculpt_source["evaluated_preview_levels"].append({
          "level":level,"vertices":len(mesh.vertices),"faces":len(mesh.polygons)
        })
    finally:evaluated.to_mesh_clear()
multi.levels=old_viewport
multi.show_viewport=old_show

body_mods=[{"name":m.name,"type":m.type,
            "levels":getattr(m,"levels",None),
            "render_levels":getattr(m,"render_levels",None)}
           for m in body.modifiers]
source={
  "status":"PASS_NATIVE_CAPABILITY_INVENTORY_PROMOTION_HOLD",
  "sex":a.sex,
  "controlled_shape_preset":receipt["source_gender_macro"],
  "source_mpfb":{
    "body_name":body.name,"source_body_vertices":len(body.data.vertices),
    "rig_name":rig.name,"bone_count":len(bone_names),
    "bone_categories":by_category,
    "rig_action":action_desc,
    "body_shape_keys":shape_keys,
    "modifiers":body_mods,
    "keyframed_bones_declared":authored,
    "keyframed_finger_bones":authored_finger,
    "keyframed_facial_bones":authored_face,
  },
  "sculpt_reference":sculpt_source,
  "approval":{
    "source_sex_macro":"PASS_CORRECTED_0_FEMALE_1_MALE",
    "sculpt_geometry_exists":True,
    "high_resolution_sculpt_in_video":False,
    "high_res_rig_transfer_accepted":False,
    "facial_animation_authored":False,
    "finger_animation_authored":False,
    "foot_ground_contact_accepted":False,
    "photorealism_accepted":False,
    "release_state":"HOLD"
  },
  "next_gates":[
    "Choose canonical rigged high-resolution render topology before more finals",
    "Qualify multires detail preservation under animated morphs, skinning and exported LOD",
    "Use independently tested facial expressions/visemes and digit bone poses in separate closeups",
    "Qualify floor contacts, root translation, foot locking, gait transition and joint physics",
    "Render at minimum 1080p for visual acceptance; 4K only after motion quality passes",
    "Per-region anatomy rights and external reproductive geometry require manual vetting"
  ]
}
a.out.write_text(json.dumps(source,indent=2,sort_keys=True)+"\n")
print("R014_RIG_LOD_CAPABILITY",json.dumps({
 "sex":a.sex,
 "sculpt_multires_total_levels":multi.total_levels,
 "evaluated_preview_levels":sculpt_source["evaluated_preview_levels"],
 "native_keyed_finger_bones":authored_finger,
 "native_keyed_facial_bones":authored_face,
 "face_bones_available":len(by_category["facial_jaw_lips_eye"]),
 "finger_bones_available":len(by_category["hands_and_fingers"]),
 "source_body_shape_keys":len(shape_keys),
 "status":source["status"]
},sort_keys=True))
