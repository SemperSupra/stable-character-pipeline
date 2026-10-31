"""Original-public W7A native video -> source-safe scene contract and release HOLD."""
import argparse, hashlib, json, re
from pathlib import Path

def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def assert_gate(ok, code):
    if not ok: raise ValueError(code)

def join(folder, revision, release_bin, output):
    p=Path(folder); o=Path(output)
    assert_gate(bool(re.fullmatch(r"[0-9a-f]{40}",revision)), "REVISION_INVALID")
    src=read(p/"source.json")
    n=read(p/"source_motion_receipt.json")
    r=read(p/"rendered/native_render_receipt.json")
    q=read(p/"rendered/independent_cross_camera_rollup.json")
    assert_gate(src.get("schema")=="scp.walk_w7a_original_approach.v1" and src.get("rights")=="ORIGINAL_SELF_AUTHORED_SYNTHETIC" and src.get("profile")=="forward","SOURCE_RIGHTS_OR_PROFILE")
    actors=src.get("actors",[])
    assert_gate(len(actors)==2 and len(set(a["id"].lower() for a in actors))==2 and all(len(a["frames"])==24 for a in actors) and src.get("fps_num")==12,"SOURCE_ACTORS_OR_CLOCK")
    source_hash=sha(p/"source.json")
    glb=p/"original_synthetic_24frame_skinned.glb"
    blend=p/"original_source_grounded_24frame_native.blend"
    assert_gate(n.get("source_sha256")==source_hash and n.get("glb_sha256")==sha(glb) and n.get("blend_sha256")==sha(blend) and n.get("frame_count")==24 and n.get("fps_num")==12,"NATIVE_OR_SOURCE_HASH")
    assert_gate(n.get("full_body")=="FAIL_ABSTRACT_LIMBS_ONLY" and n.get("human_anatomy")=="UNKNOWN_NO_INDEPENDENT_JCS_OR_ROM","FIRST_FAILURE_NOT_PRESERVED")
    assert_gate(r.get("source_motion_sha256")==source_hash and r.get("rights")=="ORIGINAL_SELF_AUTHORED_SYNTHETIC" and q.get("source_motion_sha256")==source_hash and q.get("status")=="PASS_ALL_REQUIRED_VIEWS_L1_ONLY","RENDER_OR_VIDEO_JOIN")
    cameras=("OriginalFront","OriginalOblique")
    assert_gate({x.get("camera") for x in r.get("cameras",[])}==set(cameras) and {x.get("camera") for x in q.get("cameras",[])}==set(cameras),"REQUIRED_CAMERAS")
    video_hashes={}
    for camera in cameras:
        a=next(x for x in r["cameras"] if x["camera"]==camera)
        b=next(x for x in q["cameras"] if x["camera"]==camera)
        digest=sha(p/"rendered"/(camera+".mp4"))
        assert_gate(a.get("video_sha256")==digest and b.get("video_sha256")==digest and a.get("frame_count")==24 and b.get("status")=="PASS_L1_VIDEO_ONLY","VIDEO_SHA_L1_OR_CLOCK")
        video_hashes[camera]=digest
    assert_gate(Path(release_bin).is_file(),"RELEASE_BINARY_NOT_BUILT")
    scene={"schema":"scp.scene.v1","revision":revision,"action":"walk_approach","fps":12,"frames":24,
        "actors":[{"id":a["id"],"asset_digest":"sha256:"+n["glb_sha256"],"source_class":"public-synthetic"} for a in actors],
        "cameras":list(cameras)}
    o.mkdir(parents=True,exist_ok=True)
    payload=json.dumps(scene,sort_keys=True,indent=2)+"\n"
    (o/"scene.json").write_text(payload)
    witness={"schema":"scp.rc0.w7a_source_native_video_join.v1","source_sha256":source_hash,
        "glb_sha256":n["glb_sha256"],"blend_sha256":n["blend_sha256"],
        "video_sha256":video_hashes,"full_body":n["full_body"],
        "human_anatomy":n["human_anatomy"],"original_video_l1":q["status"],
        "private_r009":"NOT_RUN_NOT_ADMITTED","artifact_custody":"PENDING_INDEPENDENT_REMOTE_REHYDRATION"}
    (o/"witness.json").write_text(json.dumps(witness,sort_keys=True,indent=2)+"\n")
    def evidence(status, path=None):
        return {"status":status,**({"receipt_sha":"sha256:"+sha(path)} if path else {})}
    manifest={"schema":"scp.release-manifest.v1","phase":"draft","scope":"public-synthetic","source_sha":revision,
        "gates":{"build":evidence("PASS",release_bin),"contract":evidence("PASS",o/"scene.json"),
        "source_motion":evidence("PASS",glb),"render":evidence("PASS",o/"witness.json"),
        "behavior":evidence("FAIL",p/"source_motion_receipt.json"),"audiences":evidence("UNKNOWN"),
        "security":evidence("UNKNOWN"),"custody":evidence("UNKNOWN"),"deployment":evidence("UNKNOWN")}}
    (o/"manifest.draft.json").write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n")
    return witness,manifest

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--folder",required=True);ap.add_argument("--revision",required=True)
    ap.add_argument("--release-binary",required=True);ap.add_argument("--output",required=True)
    x=ap.parse_args()
    witness,manifest=join(x.folder,x.revision,x.release_binary,x.output)
    print("RC0_SYNTHETIC_NATIVE_JOIN_COMPLETED_RELEASE_HELD",witness["full_body"],manifest["phase"])
