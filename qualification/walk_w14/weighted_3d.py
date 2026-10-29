"""Original 3D weighted two-avatar Blender -> GLB -> fresh Blender numeric qualification.

Builds *actual* two-bone weighted deforming meshes with nonplanar vertices,
animated quaternion pose and one-to-one reimport vertex correspondence by
unique rest-space geometry. Does not use real people, media or private source.
"""
import argparse,hashlib,json,math
from pathlib import Path
import bpy
from mathutils import Quaternion

SOURCE="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
FRAMES=(0,12,24,36,48,60,71)
FPS=12

def add_actor(name,x,profile,phase):
    data=bpy.data.armatures.new(name+"_ArmatureData")
    arm=bpy.data.objects.new(name+"_Skeleton",data)
    bpy.context.scene.collection.objects.link(arm)
    arm.location=(x,0,0)
    bpy.context.view_layer.objects.active=arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    parent=data.edit_bones.new("upper")
    parent.head=(0,0,1.40);parent.tail=(0,0,.80)
    child=data.edit_bones.new("lower")
    child.head=(0,0,.80);child.tail=(0,0,.20)
    child.parent=parent;child.use_connect=True
    bpy.ops.object.mode_set(mode="OBJECT")
    for b in arm.pose.bones:b.rotation_mode="QUATERNION"
    verts=[];faces=[]
    levels=[1.34,1.12,.91,.80,.69,.48,.27]
    for z in levels:
        # deliberately nonplanar and asymmetric per-vertex depth.
        verts.extend([(-.10,-.07,z),(.08,-.065,z),
                      (.095,.085,z),(-.085,.080,z)])
    for r in range(len(levels)-1):
        for c in range(4):
            a=r*4+c; b=r*4+(c+1)%4
            d=(r+1)*4+c; e=(r+1)*4+(c+1)%4
            faces.extend([(a,d,b),(b,d,e)])
    mesh=bpy.data.meshes.new(name+"_source_mesh")
    mesh.from_pydata(verts,[],faces);mesh.update()
    for face in mesh.polygons:face.use_smooth=True
    obj=bpy.data.objects.new(name+"_SkinnedMesh",mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent=arm
    upper=obj.vertex_groups.new(name="upper")
    lower=obj.vertex_groups.new(name="lower")
    for k,z in enumerate(levels):
        u=1 if z>=.91 else (0 if z<=.48 else (.50 if z==.80 else .25))
        l=1-u
        if u>0:upper.add(list(range(k*4,k*4+4)),u,"REPLACE")
        if l>0:lower.add(list(range(k*4,k*4+4)),l,"REPLACE")
    mod=obj.modifiers.new("OriginalArmatureSkin","ARMATURE");mod.object=arm
    arm["source_rights"]=SOURCE
    obj["source_rights"]=SOURCE
    for f in FRAMES:
        bpy.context.scene.frame_set(f)
        t=f/12.0
        # Ensure exact neutral world/rest at source t=0 for both distinct actors;
        # later frames still have independent nonplanar quaternion deformation.
        primary=.24*(math.sin(2*math.pi*t/3+phase)-math.sin(phase))
        secondary=.31*(math.sin(2*math.pi*t/3+phase+.37)-math.sin(phase+.37))
        # XYZW is the export representation; Blender native mathutils stores WXYZ.
        # Two different axes and parent-linked bones make genuine 3D deformations.
        if profile=="forward":
            qu=Quaternion((1,0,0),primary)
            ql=Quaternion((0,0,1),secondary)
        else:
            qu=Quaternion((0,1,0),primary)
            ql=Quaternion((1,0,0),secondary)
        arm.pose.bones["upper"].rotation_quaternion=qu
        arm.pose.bones["lower"].rotation_quaternion=ql
        arm.pose.bones["upper"].keyframe_insert(data_path="rotation_quaternion",frame=f)
        arm.pose.bones["lower"].keyframe_insert(data_path="rotation_quaternion",frame=f)
    return arm,obj

def evaluated_points(obj,frame):
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    deps=bpy.context.evaluated_depsgraph_get()
    ev=obj.evaluated_get(deps)
    mesh=ev.to_mesh()
    try:return [tuple(ev.matrix_world@v.co) for v in mesh.vertices]
    finally:ev.to_mesh_clear()

def min_pair_match(reference,candidate):
    # Fail-closed unique one-to-one correspondence; set matching avoids assuming
    # glTF importer retains vertex indices after normal/triangulation conversion.
    if len(reference)!=len(candidate):raise ValueError("GLB_VERTEX_COUNT_OR_SPLIT_CHANGED")
    remaining=set(range(len(candidate)))
    mapping=[]
    for a in reference:
        best=min(remaining,key=lambda idx:math.dist(a,candidate[idx]))
        error=math.dist(a,candidate[best])
        if error>2e-5:
            print("W14_REIMPORT_FIRST_FRAME_MISMATCH",json.dumps({
                "original":a,"closest_imported":candidate[best],
                "error":error,
                "source_count":len(reference),
                "import_count":len(candidate),
                "first_original":reference[:3],
                "first_imported":candidate[:3],
            }),flush=True)
            raise ValueError("GLB_REST_VERTEX_CORRESPONDENCE_FAIL")
        mapping.append(best);remaining.remove(best)
    if remaining:raise ValueError("NON_BIJECTIVE_VERTEX_MAP")
    return mapping

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--profile",choices=["forward","outward"],required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    scene.render.fps=FPS
    scene.frame_start=0;scene.frame_end=71
    assets={}
    for i,(name,x) in enumerate([("CobaltOriginal",-1.65),("MarigoldOriginal",1.65)]):
        arm,obj=add_actor(name,x,args.profile,i*.73)
        assets[name]=(arm,obj)
    native={name:{str(f):evaluated_points(obj,f) for f in FRAMES} for name,(_,obj) in assets.items()}
    if any(len(v["0"])!=28 for v in native.values()):raise ValueError("ORIGINAL_MESH_INDEX_COUNT")
    for name,(_,obj) in assets.items():
        vertex_assignments=[len(vertex.groups) for vertex in obj.data.vertices]
        if min(vertex_assignments)<1 or max(vertex_assignments)<2:
            raise ValueError("EXPECTED_SINGLE_AND_DUAL_WEIGHTED_VERTICES")
    # Recalculate all world transforms for saved scene.
    scene.frame_set(0)
    blend=out/"original_two_weighted_3d_characters.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()))
    glb=out/"original_two_weighted_3d_characters.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb.resolve()),export_format="GLB",export_animations=True)
    if glb.stat().st_size<1000 or blend.stat().st_size<10000:
        raise ValueError("MISSING_REAL_GLTF_OR_EDITABLE_BLEND")
    # Independent native readback from freshly imported GLB, not same in-memory
    # object, evaluated through Blender's imported skinning modifier.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps=FPS
    bpy.ops.import_scene.gltf(filepath=str(glb.resolve()))
    imported={}
    for obj in bpy.data.objects:
        if obj.type=="MESH" and any(m.type=="ARMATURE" for m in obj.modifiers):
            imported[obj.name.split("_SkinnedMesh")[0]]=obj
    if set(imported)!=set(assets):raise ValueError("GLB_SKIN_OBJECT_NAMES_OR_COUNTS")
    if len([x for x in bpy.data.objects if x.type=="ARMATURE"])!=2:
        raise ValueError("GLB_ARMATURE_MISSING")
    if not bpy.data.actions:raise ValueError("GLB_IMPORTED_ANIMATION_MISSING")
    max_err=0.
    minimum_motion=math.inf
    imported_count=0
    for name,obj in imported.items():
        rest=evaluated_points(obj,FRAMES[0])
        mapping=min_pair_match(native[name][str(FRAMES[0])],rest)
        moved=0.
        for f in FRAMES:
            actual=evaluated_points(obj,f)
            expected=native[name][str(f)]
            if len(actual)!=len(mapping):raise ValueError("GLB_FRAME_VERTEX_TOPOLOGY_CHANGED")
            for src_idx,dest_idx in enumerate(mapping):
                e=math.dist(actual[dest_idx],expected[src_idx])
                max_err=max(max_err,e)
                if e>5e-4:
                    print("W14_ANIMATION_PARITY_FIRST_FAILURE",json.dumps({
                        "actor":name,"frame":f,"src_vertex":src_idx,
                        "dst_vertex":dest_idx,"expected":expected[src_idx],
                        "actual":actual[dest_idx],"error":e,
                        "max_before":max_err,
                    }),flush=True)
                    raise ValueError("GLB_REIMPORT_WEIGHTED_3D_VERTEX_PARITY_FAIL")
            moved=max(moved,max(math.dist(a,b) for a,b in zip(expected,native[name]["0"])))
            imported_count+=len(mapping)
        minimum_motion=min(minimum_motion,moved)
    if minimum_motion<.02:raise ValueError("STATIC_OR_DETACHED_WEIGHTED_SKIN")
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    receipt={"schema":"scp.walk_w14_original_weighted_3d_glb.v1",
             "status":"PASS_BLENDER_NATIVE_TWO_WEIGHTED_3D_AND_GLB_REIMPORT",
             "source_rights":SOURCE,"profile":args.profile,
             "actors":2,"bones_per_actor":2,"vertices_per_actor":28,
             "source_frame_numbers":list(FRAMES),"fps":FPS,
             "imported_evaluated_vertex_observations":imported_count,
             "maximum_world_vertex_error":max_err,
             "minimum_actor_deformation":minimum_motion,
             "rest_vertex_correspondence":"ONE_TO_ONE_BY_SPATIAL_MATCH_AT_SOURCE_T0",
             "quat_representation":"Blender WXYZ native; glTF XYZW serialized",
             "true_xyz_deformation":True,"weighted_mesh":True,
             "source_motion":"ORIGINAL_ARTIFICIAL_TEST_ROTATIONS_NOT_HUMAN_GAIT",
             "body_contact":"NOT_QUALIFIED","character_identity":"NOT_APPLICABLE",
             "independent_non_blender_reader":"NOT_YET_QUALIFIED",
             "blend_sha256":sha(blend),"glb_sha256":sha(glb)}
    (out/"native_3d_skin_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print("W14_WEIGHTED_TWO_AVATAR_GLB_PASS",json.dumps(receipt,sort_keys=True))
if __name__=="__main__":main()
