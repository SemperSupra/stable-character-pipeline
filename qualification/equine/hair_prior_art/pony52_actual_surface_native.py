#!/usr/bin/env python3
"""Experimental 5.2 direct attachment to ORIGINAL 30-joint skinned groom.

Native mode consumes an exact 4.5 .blend and six-follicle capsule. Creates an
ephemeral native CURVES object *attached to the actual animated groom mesh*;
never uses synthetic moving spheres. Read-only original sources on disk.
Separate --compare mode has NO Blender dependency and keeps body contacts,
material calibration, rights and release SCIENTIFICALLY HELD.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
from pony_source_trajectory import classify as classify_source

SCHEMA="equine.pony52.attached_original_groom_48f.v1"
REGION_TARGETS={
    "mane":("sculpt_sloping_neck","continuous_shetland_barrel_rump_shoulder"),
    "forelock":("sculpt_equine_brow_bridge_muzzle","sculpt_sloping_neck"),
    "tail":("continuous_shetland_barrel_rump_shoulder","continuous_hind_L_limb","continuous_hind_R_limb"),
}
def point(v):
    if type(v) not in (tuple,list) or len(v)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>100 for x in v):
        raise ValueError("invalid source/vector witness")
    return tuple(float(x) for x in v)
def d(a,b):
    return math.sqrt(sum((a[k]-b[k])**2 for k in range(3)))
def evaluate_pair(capsule,physics,animation):
    contract=classify_source(capsule)
    ids={g["card_id"]:g for g in capsule["guides"]}
    normalized={}
    for mode,receipt in (("physics",physics),("animation",animation)):
        if type(receipt)!=dict or receipt.get("schema")!=SCHEMA or receipt.get("mode")!=mode:
            raise ValueError("wrong attached-groom native schema/mode")
        if receipt.get("source_blend_sha256")!=capsule["source_blend_sha256"] or receipt.get("source_capsule_sha256")!=contract["source_capsule_sha256"]:
            raise ValueError("incorrect original rig and follicle source")
        if receipt.get("source_surface")!="geometric_coat_mane_tail" or receipt.get("source_surface_has_armature_skin") is not True or receipt.get("curves_surface_binding_confirmed") is not True:
            raise ValueError("not an actual original skinned surface")
        if receipt.get("source_cards_total")!=1050 or receipt.get("source_bones")!=30 or receipt.get("captured_rest_geometry") is not True or receipt.get("surface_unique_anchor_uv") is not True:
            raise ValueError("invalid original rig/attachment ABI")
        if receipt.get("source_kind")!="original_synthetic" or receipt.get("science_hold")!="KEEP" or receipt.get("release_admission") is not False or receipt.get("full_body_collision_accepted") is not False:
            raise ValueError("source rights/science hold bypass")
        if receipt.get("errors") or receipt.get("status")!="48F_ORIGINAL_SKIN_GROOM_NATIVE_GEOMETRY_OBSERVED":
            raise ValueError("native output incomplete or contains errors")
        if receipt.get("frame_count")!=48 or receipt.get("guide_count")!=6 or type(receipt.get("frames"))!=list or len(receipt["frames"])!=48:
            raise ValueError("incomplete real surface frames")
        observed=[]
        for fi,frame in enumerate(receipt["frames"]):
            if type(frame)!=dict or frame.get("frame")!=fi+1 or type(frame.get("guides"))!=list or len(frame["guides"])!=6:
                raise ValueError("reordered actual source 48f")
            row={}
            for g in frame["guides"]:
                if type(g)!=dict or set(g)!={"card_id","region","source_root_m","actual_root_m","actual_tip_m","tip_minus_root_m","root_error_m","tip_to_body_nearest_m","segment_surface_ray_hits","curve_polyline_length_m"}:
                    raise ValueError("unknown source geometry or evidence")
                card=g["card_id"]
                if type(card)!=int or card not in ids or card in row or g["region"]!=ids[card]["region"]:
                    raise ValueError("wrong original follicle identity")
                expected=point(ids[card]["samples"][fi]["root_m"])
                claim=point(g["source_root_m"])
                root=point(g["actual_root_m"])
                tip=point(g["actual_tip_m"])
                rel=point(g["tip_minus_root_m"])
                if d(expected,claim)>0.000001 or d(tuple(tip[k]-root[k] for k in range(3)),rel)>0.000002:
                    raise ValueError("forged source or relative movement")
                err=g["root_error_m"]
                distbody=g["tip_to_body_nearest_m"]
                hits=g["segment_surface_ray_hits"]
                length=g["curve_polyline_length_m"]
                if type(err) not in (int,float) or not math.isfinite(err) or abs(err-d(root,expected))>.000002:
                    raise ValueError("incorrect actual follicle root error")
                if type(distbody) not in (int,float) or not math.isfinite(distbody) or not 0<=distbody<100:
                    raise ValueError("no measured actual body proximity")
                if type(hits)!=int or not 0<=hits<=50:
                    raise ValueError("invalid potential segment/body crossing count")
                if type(length) not in (float,int) or not math.isfinite(length) or not .01<length<3:
                    raise ValueError("invalid source-evaluated strand length")
                if err>.015:
                    raise ValueError("actual animated groom follicle detached more than 15mm")
                row[card]={"rel":rel,"len":float(length),"body_dist":float(distbody),"hits":hits}
            if set(row)!=set(ids):raise ValueError("missing original source hair guide")
            observed.append(row)
        normalized[mode]=observed
    physics=normalized["physics"];animation=normalized["animation"]
    motion={};rigid={};strain={};bodynear={};crossings={}
    for region in REGION_TARGETS:
        cards=[id for id,g in ids.items() if g["region"]==region]
        motion[region]=max(d(physics[f][id]["rel"],physics[0][id]["rel"]) for id in cards for f in range(48))
        rigid[region]=max(d(animation[f][id]["rel"],animation[0][id]["rel"]) for id in cards for f in range(48))
        strain[region]=max(abs(physics[f][id]["len"]/d(point(ids[id]["samples"][0]["root_m"]),point(ids[id]["samples"][0]["tip_m"]))-1.)
                           for id in cards for f in range(48))
        bodynear[region]=min(physics[f][id]["body_dist"] for id in cards for f in range(48))
        crossings[region]=sum(physics[f][id]["hits"] for id in cards for f in range(48))
    if max(rigid.values())>.0002:
        raise ValueError("native rigid control unexpectedly has independent motion")
    if max(motion.values())<.001:
        raise ValueError("original-skinned XPBD hair not distinguished from rigid control")
    warnings=["SKIN_GROOM_SURFACE_NOT_A_WATERTIGHT_BODY",
              "BVH_SEGMENT_HITS_AND_TIP_DISTANCE_NOT_SIGNED_PENETRATION",
              "ONLY_SIX_GUIDES_NO_FOLLOWER_LOD_OR_MATERIAL_CALIBRATION",
              "COLLISION_PRESSURE_HAIR_SELF_COLLISION_AND_WIND_NOT_VALIDATED"]
    if max(strain.values())>.10:
        warnings.append("SKIN_GROOM_ROD_LENGTH_STRAIN_GT_10PCT")
    return {"schema":"equine.pony52.attached_original_groom.paired_quality.v1",
        "source_blend_sha256":capsule["source_blend_sha256"],
        "source_capsule_sha256":contract["source_capsule_sha256"],
        "guides":6,"frames":48,
        "max_physics_relative_motion_m_by_region":{k:round(x,7) for k,x in motion.items()},
        "max_rigid_control_relative_motion_m_by_region":{k:round(x,7) for k,x in rigid.items()},
        "max_physics_polyline_length_strain_fraction_by_region":{k:round(x,7) for k,x in strain.items()},
        "min_tip_body_unsigned_distance_m_by_region":{k:round(x,7) for k,x in bodynear.items()},
        "potential_body_segment_ray_hits_by_region":crossings,
        "warnings":warnings,"status":"ATTACHED_ORIGINAL_SKIN_48F_ENGINEERING_PROOF_ONLY",
        "physical_material_calibration":"UNKNOWN","full_anatomical_collision_clearance":False,
        "visual_acceptance":False,"science_hold":"KEEP","release_admission":False}

def main_native(args):
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    if len(args)!=3:raise SystemExit("usage: --native source.blend capsule.json receipt.json")
    source,capsule_file,out=map(Path,args)
    if not source.is_file() or not capsule_file.is_file() or out.exists():
        raise ValueError("source/receipt missing or output would overwrite")
    if not 4096<source.stat().st_size<300_000_000:
        raise ValueError("bad original blend")
    capsule=json.loads(capsule_file.read_text())
    contract=classify_source(capsule)
    if hashlib.sha256(source.read_bytes()).hexdigest()!=capsule["source_blend_sha256"]:
        raise ValueError("source blend did not match original 4.5 tested native result")
    mode=os.environ.get("SCP_52_MODE","physics")
    if mode not in ("physics","animation"):raise ValueError("unrecognized native physics mode")
    out.parent.mkdir(parents=True,exist_ok=True)
    receipt={"schema":SCHEMA,"mode":mode,"source_kind":"original_synthetic",
        "source_blend_sha256":capsule["source_blend_sha256"],
        "source_capsule_sha256":contract["source_capsule_sha256"],
        "source_surface":"geometric_coat_mane_tail",
        "source_cards_total":1050,"source_bones":30,
        "source_surface_has_armature_skin":False,"curves_surface_binding_confirmed":False,
        "captured_rest_geometry":False,"surface_unique_anchor_uv":False,
        "frame_count":0,"guide_count":6,"frames":[],"errors":[],
        "science_hold":"KEEP","release_admission":False,"full_body_collision_accepted":False,
        "status":"NOT_TESTED"}
    stage="open_unchanged_original_source"
    start=time.perf_counter()
    try:
        if bpy.app.version[:3]!=(5,2,3):raise ValueError("native Blender version not exact 5.2.3")
        bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
        scene=bpy.context.scene
        rig=bpy.data.objects.get("PonyRig30")
        groom=bpy.data.objects.get("geometric_coat_mane_tail")
        if rig is None or rig.type!="ARMATURE" or len(rig.data.bones)!=30 or groom is None or groom.type!="MESH" or len(groom.data.vertices)!=10500:
            raise ValueError("missing native 30j skinned curved hair")
        if not any(m.type=="ARMATURE" and m.object==rig for m in groom.modifiers):
            raise ValueError("original long hair source skin not present")
        receipt["source_surface_has_armature_skin"]=True
        if len(groom.data.polygons)!=1050*8:
            raise ValueError("source grooming triangle topology changed")
        scene.frame_set(0);scene.frame_set(1)
        bpy.context.view_layer.update()
        stage="construct_original_unique_uv_root_anchors"
        # Each of 1050 source cards receives its own UV tile; NEVER reuse
        # the render UV set, where all cards deliberately overlap.
        uv=groom.data.uv_layers.new(name="SCP_OriginalCardAttachmentUV")
        for poly in groom.data.polygons:
            for li in poly.loop_indices:
                i=groom.data.loops[li].vertex_index
                card,corner=divmod(i,10)
                uv.data[li].uv=((card%35+(corner%2))/35.,(card//35+corner//2/4.)/30.)
        receipt["surface_unique_anchor_uv"]=True
        # Evaluate original source rest centerline, not an invented straight
        # rod, before creating the experimental curves object.
        deps=bpy.context.evaluated_depsgraph_get()
        ev=groom.evaluated_get(deps);mesh=ev.to_mesh()
        rest={}
        try:
            world=ev.matrix_world.copy()
            for g in capsule["guides"]:
                card=g["card_id"];row=[]
                for k in range(5):
                    i=card*10+2*k
                    p=world@((mesh.vertices[i].co+mesh.vertices[i+1].co)*.5)
                    row.append(p)
                if (row[0]-Vector(g["samples"][0]["root_m"])).length>.005:
                    raise ValueError("source f1 longhair root differs from capsule")
                rest[card]=row
        finally:
            ev.to_mesh_clear()
        stage="add_native_curves_on_real_original_groom_surface"
        bpy.ops.object.select_all(action="DESELECT")
        groom.select_set(True);bpy.context.view_layer.objects.active=groom
        bpy.ops.object.curves_empty_hair_add()
        hair=bpy.context.object
        if hair is None or hair.type!="CURVES":
            raise ValueError("native original surface hair object missing")
        hair.name="ShetlandActualAnimatedSkinnedGroomHair"
        data=hair.data
        if data.surface!=groom:
            raise ValueError("native curves did not attach to selected skinned original groom")
        data.surface_uv_map=uv.name
        receipt["curves_surface_binding_confirmed"]=True
        capture=[m for m in groom.modifiers if m.type=="NODES" and m.node_group and "Capture Rest Geometry" in m.node_group.name]
        receipt["source_modifier_stack"]=[{"name":m.name,"type":m.type} for m in groom.modifiers]
        if not capture:
            raise ValueError("real original groom surface Capture Rest Geometry missing")
        receipt["captured_rest_geometry"]=True
        guides=capsule["guides"]
        data.add_curves([6]*len(guides))
        if len(data.curves)!=6 or len(data.points)!=36:
            raise ValueError("real source native guide cardinality")
        att=data.attributes.get("surface_uv_coordinate")
        if att is None:
            att=data.attributes.new(name="surface_uv_coordinate",type="FLOAT2",domain="CURVE")
        if att.domain!="CURVE" or att.data_type!="FLOAT2":
            raise ValueError("native hair UV attachment attribute unexpected")
        inv=hair.matrix_world.inverted()
        for i,g in enumerate(guides):
            card=g["card_id"]
            centerline=rest[card]
            for j in range(6):
                t=j*4/5;low=min(3,int(t));amount=t-low
                p=centerline[low].lerp(centerline[low+1],amount)
                data.points[i*6+j].position=inv@p
                data.points[i*6+j].radius=.002*(1-.8*j/5)
            # A tiny inner-face offset avoids ambiguous adjacent UV island
            # boundaries; source mismatch is explicitly measured at every f.
            att.data[i].vector=((card%35+.5)/35.,(card//35+.002)/30.)
        data.update_tag()
        stage="bind_native_experimental_hair_dynamics"
        dynamics=[m for m in hair.modifiers if m.type=="NODES" and m.node_group and "Hair Dynamics" in m.name]
        if len(dynamics)!=1:
            raise ValueError("native experimental Hair Dynamics asset not found")
        old=dynamics[0];private=old.node_group.copy()
        private.name="SCP_RealGroomXPBD_"+mode
        sockets=[x for x in private.interface.items_tree if x.item_type=="SOCKET" and x.in_out=="INPUT" and x.name.strip().lower()=="mode"]
        if len(sockets)!=1:raise ValueError("experimental native Mode socket absent")
        mode_str="Physics (Experimental)" if mode=="physics" else "Animation"
        sockets[0].default_value=mode_str
        if sockets[0].default_value!=mode_str:raise ValueError("experimental native Mode failed readback")
        hair.modifiers.remove(old)
        mod=hair.modifiers.new(name="SCP_RealSource_"+mode,type="NODES");mod.node_group=private
        receipt["modifier_mode"]=mode_str
        stage="measure_48f_real_body_collision_and_source_root"
        bodyobjs={name:bpy.data.objects.get(name) for names in REGION_TARGETS.values() for name in names}
        if any(obj is None or obj.type!="MESH" for obj in bodyobjs.values()):
            raise ValueError("real pony body collision surface missing")
        def body_bvh(obj,deps):
            e=obj.evaluated_get(deps);m=e.to_mesh()
            try:
                m.calc_loop_triangles()
                ps=[tuple(e.matrix_world@v.co) for v in m.vertices]
                tris=[tuple(x.vertices) for x in m.loop_triangles]
                if not ps or not tris:raise ValueError("empty original body mesh")
                return BVHTree.FromPolygons([Vector(v) for v in ps],tris,all_triangles=True)
            finally:
                e.to_mesh_clear()
        # Calibrate first positive and negative contact rays, no invented
        # ground-truth collision clearance or signed interior classification.
        fixture=BVHTree.FromPolygons([Vector(v) for v in ((0,0,0),(1,0,0),(0,1,0))],[(0,1,2)],all_triangles=True)
        if fixture.ray_cast(Vector((.25,.25,1)),Vector((0,0,-1)),2)[0] is None or fixture.ray_cast(Vector((10,10,1)),Vector((0,0,-1)),2)[0] is not None:
            raise ValueError("BVH raycast independent positive/negative controls broken")
        scene.frame_set(0);bpy.context.view_layer.update()
        for frame in range(1,49):
            scene.frame_set(frame);bpy.context.view_layer.update()
            deps=bpy.context.evaluated_depsgraph_get()
            evalhair=hair.evaluated_get(deps)
            if evalhair.type!="CURVES" or len(evalhair.data.curves)!=6 or len(evalhair.data.points)!=36:
                raise ValueError("source original 5.2 curves/points topology lost")
            matrix=evalhair.matrix_world.copy()
            bvh={name:body_bvh(obj,deps) for name,obj in bodyobjs.items()}
            observations=[]
            for i,g in enumerate(guides):
                pts=[matrix@evalhair.data.points[6*i+j].position for j in range(6)]
                root,tip=pts[0],pts[-1]
                expected=Vector(g["samples"][frame-1]["root_m"])
                candidates=REGION_TARGETS[g["region"]]
                nearest=[]
                rayhits=0
                for name in candidates:
                    tree=bvh[name]
                    location,normal,index,dist=tree.find_nearest(tip)
                    if location is None or not math.isfinite(dist):raise ValueError("missing evaluated body proximity")
                    nearest.append(float(dist))
                    for j in range(1,6):
                        delta=pts[j]-pts[j-1]
                        length=delta.length
                        if length<=1e-8:raise ValueError("collapsed experimental native rod")
                        hit=tree.ray_cast(pts[j-1],delta.normalized(),length-1e-8)
                        if hit[0] is not None:rayhits+=1
                observations.append({
                    "card_id":g["card_id"],"region":g["region"],
                    "source_root_m":[float(v) for v in expected],
                    "actual_root_m":[float(v) for v in root],
                    "actual_tip_m":[float(v) for v in tip],
                    "tip_minus_root_m":[float(v) for v in tip-root],
                    "root_error_m":float((root-expected).length),
                    "tip_to_body_nearest_m":min(nearest),
                    "segment_surface_ray_hits":rayhits,
                    "curve_polyline_length_m":sum((pts[j]-pts[j-1]).length for j in range(1,6))})
            receipt["frames"].append({"frame":frame,"guides":observations})
        receipt["frame_count"]=len(receipt["frames"])
        maxerr=max(g["root_error_m"] for f in receipt["frames"] for g in f["guides"])
        receipt["maximum_actual_root_error_m"]=maxerr
        if maxerr>.015:
            receipt["errors"].append("native-original-groom-follicle-root-tracking-exceeds-15mm")
    except Exception as e:
        import traceback
        receipt["errors"].append(stage+":"+type(e).__name__+":"+str(e)[:300])
        receipt["traceback"]=traceback.format_exc(limit=5)[:1600]
    receipt["elapsed_s"]=round(time.perf_counter()-start,4)
    receipt["status"]="48F_ORIGINAL_SKIN_GROOM_NATIVE_GEOMETRY_OBSERVED" if not receipt["errors"] else "NATIVE_REAL_SOURCE_FAIL_CLOSED"
    out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print("PONY_52_REAL_SKIN_SURFACE",json.dumps({k:receipt.get(k) for k in ("mode","status","frame_count","guide_count","maximum_actual_root_error_m","elapsed_s","errors")},sort_keys=True))
    if receipt["errors"]:raise RuntimeError("; ".join(receipt["errors"]))

def selftest():
    # Verify minimal malformed source rejection independent of Blender.
    from pony_source_trajectory import SCHEMA as SOURCE_SCHEMA
    bad={"schema":SOURCE_SCHEMA}
    try:classify_source(bad)
    except ValueError:pass
    else:raise AssertionError("source validator accepted forged incomplete original 30j capsule")
    assert d((0,0,0),(0,3,4))==5
    try:point((0,float("nan"),1))
    except ValueError:pass
    else:raise AssertionError("accepted nonfinite native body vector")
    print("REAL_SURFACE_OFFLINE_HOSTILE_PRIMITIVES_PASS")

if __name__=="__main__":
    if len(sys.argv)<2:raise SystemExit("need --selftest / --native / --compare")
    arg=(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else sys.argv[1:])
    action,*remaining=arg
    if action=="--native":main_native(remaining)
    elif action=="--compare":
        if len(remaining)!=4:raise SystemExit("--compare capsule.json physics.json animation.json out.json")
        a,b,c=[json.loads(Path(p).read_text()) for p in remaining[:3]]
        receipt=evaluate_pair(a,b,c)
        out=Path(remaining[3])
        if out.exists():raise ValueError("will not overwrite original evidence")
        out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
        print("PONY52_TRUE_ORIGINAL_SURFACE_PAIR",json.dumps(receipt,sort_keys=True))
    elif action=="--selftest":selftest()
    else:raise SystemExit("unrecognized offline vs native command")
