#!/usr/bin/env python3
"""Independent synthetic BVH-FK -> binary VMD -> bpy receipt parity reviewer.

Read-only inputs. Explicit exact-source/target clocks, bytes, loss, ancestry,
actual renderer and scientific limitations. Does not validate human retargeting.
"""
import argparse,copy,hashlib,json,math,pathlib,struct,sys
ORIGINAL_SHA="ab3a0d712c9c4f21fba0cf0698568dd5f88f1b959cf8aae28173c6435153d760"
NAMES=("Hips","Knee","Foot")
SCHEMA="scp.r009.independent-bvh-vmd-bpy-source-parity.v1"
def digest(b):return hashlib.sha256(b).hexdigest()
def need(ok,why):
    if not ok:raise ValueError(why)
def vmd_records(blob):
    need(len(blob)>=74 and blob[:30].rstrip(b"\0")==b"Vocaloid Motion Data 0002","VMD_V2_SIGNATURE")
    count=struct.unpack_from("<I",blob,50)[0]
    need(count==6 and len(blob)==54+count*111+20,"VMD_BOUNDED_RECORD_COUNT")
    need(blob[-20:]==b"\0"*20,"VMD_NON_BONE_SECTIONS_UNADMITTED")
    out={}
    for i in range(count):
        off=54+i*111
        block=blob[off:off+111]
        rawname=block[:15]
        need(b"\0" in rawname,"VMD_UNTERMINATED_BONE")
        name=rawname.split(b"\0",1)[0].decode("ascii")
        need(name in NAMES,"VMD_BONE_UNEXPECTED")
        frame=struct.unpack_from("<I",block,15)[0]
        pos=struct.unpack_from("<fff",block,19)
        quat=struct.unpack_from("<ffff",block,31)
        need(frame in (0,1) and (name,frame) not in out,"VMD_CLOCK_DUPLICATE_OR_GAP")
        need(all(math.isfinite(x) for x in pos+quat),"VMD_NONFINITE")
        need(quat==(0.,0.,0.,1.),"VMD_ROTATION_NOT_TRANSFERRED")
        out[name,frame]=pos
    need(set(out)=={(n,i) for n in NAMES for i in (0,1)},"VMD_MISSING_KEYS")
    return out
def evaluate(fkbytes,vmdb,cross,native):
    fk=json.loads(fkbytes)
    need(fk.get("schema")=="scp.r009.original-bvh-full-frame-fk.v1","FK_SCHEMA")
    need(fk.get("source_sha256")==ORIGINAL_SHA,"BVH_ORIGINAL_SOURCE_NOT_ADMITTED")
    need(fk.get("rights")=="ORIGINAL_SELF_AUTHORED_SYNTHETIC","FK_RIGHTS")
    need(fk.get("meters_per_unit")==1 and len(fk.get("frames",[]))==3,"FK_SOURCE_SCALE_OR_CLOCK")
    need(cross.get("fk_receipt_sha256")==digest(fkbytes),"FK_BYTE_TAMPER")
    need(cross.get("bvh_source_sha256")==ORIGINAL_SHA,"FK_SOURCE_CUSTODY")
    need(cross.get("source_frames")==3 and cross.get("vmd_keys")==6,"CROSSWALK_COUNT")
    need(cross.get("target_fps")==30 and cross.get("target_frame_pairs")==[[0,0],[2,1]],"CLOCK_MAP_OR_ENDPOINT_FORGERY")
    need(cross.get("source_frame_1")=="DROPPED_30FPS_RESAMPLE","LOSS_MAP_MISSING")
    need(cross.get("synthetic_target_aliases")=={n:n for n in NAMES},"UNQUALIFIED_TARGET_ALIAS")
    need(cross.get("hierarchy_semantics")=="LOST_WORLD_TRANSLATION_ONLY_NOT_HUMAN_RETARGETING","FALSE_HIERARCHY_CLAIM")
    need(cross.get("private_R009")=="HELD_NOT_ACCEPTED","FALSE_PRIVATE_PROMOTION")
    need(cross.get("vmd_sha256")==digest(vmdb),"VMD_BYTE_TAMPER")
    recs=vmd_records(vmdb)
    diffs={}
    for nameindex,name in enumerate(NAMES):
        worlds=[]
        for i,row in enumerate(fk["frames"]):
            need(row.get("frame")==i,"FK_FRAME_INDEX")
            joints=row.get("world_joints",[])
            need(len(joints)==3 and [j["name"] for j in joints]==list(NAMES),"FK_JOINT_ROLE")
            worlds.append(joints[nameindex]["position_meters"])
        expected=[worlds[2][axis]-worlds[0][axis] for axis in range(3)]
        need(all(math.isfinite(x) for x in expected),"FK_NONFINITE")
        need(all(abs(recs[name,0][axis])<=1e-7 for axis in range(3)),"VMD_FRAME0_MUST_BE_ZERO_DELTA")
        need(max(abs(recs[name,1][axis]-expected[axis]) for axis in range(3))<1e-6,
             "TARGET_VMD_SOURCE_DELTA_MISMATCH:"+name)
        need(abs(math.dist((0,0,0),expected)-1)<1e-8,"FIXTURE_SOURCE_FK_DELTA_NOT_UNIT")
        diffs[name]=expected
    need(native.get("schema")=="scp.r009.original-bvh-vmd-native-bpy.v1","NATIVE_RECEIPT_SCHEMA")
    need(native.get("status")=="PASS_ACTUAL_BPY_MMD_TOOLS_AUTHORED_BVH_CROSSWALK_ONLY","NATIVE_STATUS")
    need(native.get("vmd_sha256")==digest(vmdb),"NATIVE_VMD_BYTE_CUSTODY")
    need(native.get("target_bone_aliases")=={n:n for n in NAMES},"NATIVE_ALIAS_DRIFT")
    need(native.get("frames")==[0,1] and native.get("lost_source_frame")=="1_of_3_dropped_explicitly","NATIVE_CLOCK_LOSS")
    need(native.get("retarget_semantics")=="LOST_WORLD_TRANSLATION_ONLY_NOT_HUMAN_RETARGETING","NATIVE_FALSE_RETARGETING")
    need(native.get("private_R009")=="HELD_NOT_ACCEPTED" and native.get("human_JCS_ROM")=="UNKNOWN" and native.get("actual_human_capture")=="NOT_ADMITTED","NATIVE_SCIENTIFIC_FALSE_PROMOTION")
    for n in NAMES:
        observed=native["bpy_bone_displacement"][n]
        skin=native["actual_skinned_mesh_displacement"][n+"_mesh"]
        magnitude=math.dist((0,0,0),diffs[n])
        need(math.isfinite(observed) and abs(observed-magnitude)<1e-5,"NATIVE_DELTA_MISMATCH:"+n)
        need(math.isfinite(skin) and abs(skin-magnitude)<1e-5,"NATIVE_SKIN_DELTA_MISMATCH:"+n)
    return {"schema":SCHEMA,
            "status":"PASS_INDEPENDENT_ORIGINAL_SYNTHETIC_SOURCE_TO_NATIVE_MAGNITUDE_ONLY",
            "source_bvh_sha256":ORIGINAL_SHA,"fk_json_sha256":digest(fkbytes),
            "vmd_sha256":digest(vmdb),"native_mmd_tools_commit":native.get("mmd_tools_commit"),
            "source_endpoint_displacements_m":diffs,
            "source_frames":3,"target_frames":2,"dropped_source_frame":1,
            "native_displacement_magnitude_checked":True,
            "native_signed_axis_direction":"NOT_IN_RECEIPT_NOT_QUALIFIED",
            "hierarchical_rotation_retargeting":"NOT_IMPLEMENTED",
            "source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
            "human_rom_jcs":"UNKNOWN","private_R009":"HELD_NOT_ACCEPTED",
            "CPE":"NOT_PROMOTED"}
def main():
    p=argparse.ArgumentParser()
    for n in ("fk","vmd","crosswalk","native","out"):p.add_argument("--"+n,required=True)
    p.add_argument("--fault",choices=("baseline","wrong_clock","false_hierarchy","altered_vmd_delta","falsified_native","false_human","bad_alias","modified_fk"),default="baseline")
    a=p.parse_args()
    fkbytes=pathlib.Path(a.fk).read_bytes()
    vmdb=pathlib.Path(a.vmd).read_bytes()
    cross=json.loads(pathlib.Path(a.crosswalk).read_bytes())
    native=json.loads(pathlib.Path(a.native).read_bytes())
    if a.fault=="wrong_clock":cross["target_frame_pairs"]=[[0,0],[1,1]]
    if a.fault=="false_hierarchy":cross["hierarchy_semantics"]="HUMAN_HIERARCHY_PRESERVED"
    if a.fault=="altered_vmd_delta":
        mutable=bytearray(vmdb)
        struct.pack_into("<f",mutable,54+111+19,0.5)
        vmdb=bytes(mutable)
        cross["vmd_sha256"]=digest(vmdb)
    if a.fault=="falsified_native":native["bpy_bone_displacement"]["Hips"]=0.
    if a.fault=="false_human":native["human_JCS_ROM"]="PASS"
    if a.fault=="bad_alias":cross["synthetic_target_aliases"]["Knee"]="L_Ankle"
    if a.fault=="modified_fk":fkbytes+=b" "
    try:
        r=evaluate(fkbytes,vmdb,cross,native)
        if a.fault!="baseline":raise ValueError("FAULT_FALSE_ACCEPT:"+a.fault)
        r["input_blobs_sha256"]={n:digest(pathlib.Path(getattr(a,n)).read_bytes()) for n in ("fk","vmd","crosswalk","native")}
        with pathlib.Path(a.out).open("x",encoding="utf8") as f:
            json.dump(r,f,sort_keys=True,indent=2);f.write("\n")
        print(json.dumps(r,sort_keys=True))
    except (ValueError,KeyError,IndexError,TypeError,struct.error,UnicodeError) as exc:
        print("INDEPENDENT_CROSSWALK_REJECT:"+str(exc),file=sys.stderr)
        raise SystemExit(2)
if __name__=="__main__":main()
