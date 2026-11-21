"""N03D-AF true evaluated CC0 shoe heel/toe *proxies* from target toe-bone direction.

Original Aster/Juniper rig source and action unchanged, no approved anatomy.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy

HERE=Path(__file__).parent
sys.path.insert(0,str(HERE))
from sole import project,snapshot,assess

def require(ok,code):
    if not ok:raise RuntimeError(code)

def hashfile(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def seek(t):
    v=t*12
    n=int(math.floor(v+1e-8))
    bpy.context.scene.frame_set(n,subframe=v-n)
    bpy.context.view_layer.update()

def actual_mesh(shoe):
    obj=shoe.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=obj.to_mesh()
    try:
        require(len(mesh.vertices)==len(shoe.data.vertices),"VERTEX_TOPOLOGY_NOT_STABLE")
        return [[float(v) for v in obj.matrix_world@x.co] for x in mesh.vertices]
    finally:obj.to_mesh_clear()

def boneworld(rig,name):
    p=rig.matrix_world@rig.pose.bones[name].head
    return [float(p.x),float(p.y),float(p.z)]

def main():
    ap=argparse.ArgumentParser()
    for n in ("scene","sha","wardrobe","retarget","trace","corr","out"):
        ap.add_argument("--"+n,required=True)
    a=ap.parse_args(sys.argv[sys.argv.index("--")+1:])
    require(hashfile(a.scene)==a.sha,"SCENE_SHA")
    sc=bpy.context.scene
    require(sc.get("r078_source")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and
            sc.get("r082_wardrobe")=="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL","ORIGINAL_CC0_RIGHTS")
    ward=json.loads(Path(a.wardrobe).read_text())
    rec=json.loads(Path(a.retarget).read_text())
    tr=json.loads(Path(a.trace).read_text())
    corr=json.loads(Path(a.corr).read_text())
    require(rec["candidate_blend_sha256"]==a.sha and rec["input_scene_sha256"]==ward["blend_sha256"] and
            tr["source_scene_sha256"]==a.sha and corr["source_scene_sha256"]==a.sha and
            corr["source_trace_sha256"]==hashfile(a.trace),"SOURCE_PROVENANCE_JOIN")
    observed=[]
    for actor in ward["characters"]:
        name=actor["name"]
        require(name in ("AsterOriginal","JuniperOriginal"),"ONLY_ORIGINAL_FICTIONAL")
        rig=bpy.data.objects.get(name+"_MPFBRig")
        require(rig is not None and len(rig.data.bones)==163,"NATIVE_RIG")
        matches=[x for x in actor["garments"] if x["pack"]=="shoes01"]
        require(len(matches)==1,"REAL_CC0_SHOE")
        shoe=bpy.data.objects[matches[0]["native_object"]]
        require(any(x.type=="ARMATURE" and x.object==rig for x in shoe.modifiers),"SHOE_NOT_SKINNED")
        rest_x=[float(v.co.x) for v in shoe.data.vertices]
        middle=(min(rest_x)+max(rest_x))*.5
        for start in (24,48):
            # Force serial evaluation to preserve historic R090 source rig state.
            for i in range(start+1):seek(i/24)
            for side in ("L","R"):
                foot="foot."+side
                toe="toe1-1."+side
                require(foot in rig.pose.bones and toe in rig.pose.bones,"NATIVE_FOOT_TOE_BONES_MISSING")
                fp=boneworld(rig,foot)
                tp=boneworld(rig,toe)
                forward=(tp[0]-fp[0],tp[1]-fp[1])
                sideids=[i for i,x in enumerate(rest_x) if (x>=middle)==(side=="L")]
                ids=project(actual_mesh(shoe),sideids,forward)
                data={"heel":[],"toe":[]}
                for j in range(12):
                    t=(start+j)/24
                    seek(t)
                    xyz=actual_mesh(shoe)
                    for lbl in ("heel","toe"):
                        s=snapshot(xyz,ids[lbl+"_proxy_vertex_ids"])
                        data[lbl].append({"t_s":t,**s})
                observed.append({"actor":name,"side":side,"start_24hz":start,"cohort":ids,
                                 "heel_samples":data["heel"],"toe_samples":data["toe"],
                                 "toe_bone_label_verified":False,
                                 "source_foot_to_toe_axis_xy_m":list(forward)})
    output={"schema":"scp.n03d-af.real-shoe-plantar-proxy.v1","source_class":"ORIGINAL_FICTIONAL_CC0",
            "source_scene_sha256":a.sha,"trace_sha256":hashfile(a.trace),
            "correspondence_sha256":hashfile(a.corr),
            "source_scene_unchanged":True,"actual_anatomy_accepted":False,
            "physical_ground_force_available":False,
            "mvp_accepted":False,"windows":observed}
    Path(a.out).write_text(json.dumps(output,sort_keys=True,allow_nan=False)+"\n")
    judged=assess(output)
    Path(a.out+".critic.json").write_text(json.dumps(judged,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("N03D_AF_TRUE_NATIVE_SHOE_BONE_AXIS_PROXIES",
          json.dumps({"windows":judged["windows"],"status":judged["status"]},sort_keys=True),flush=True)
    require(judged["status"]=="HOLD" and len(judged["windows"])==8,"FALSE_CONTACT_PROMOTION")

if __name__=="__main__":main()
