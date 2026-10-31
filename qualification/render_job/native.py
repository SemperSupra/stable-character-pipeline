"""Run one admitted original public synthetic W7A native Blender job.

The only input is an immutable git revision; no user-provided script, media URI,
private source, arbitrary path, taxon, or command is accepted from UI/API.
"""
import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path
SCHEMA="scp.native-job-result.v1"
RIGHTS="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
CAMERAS=("OriginalFront","OriginalOblique")
ACTORS=("CobaltOriginal","MarigoldOriginal")
ROOT=Path(__file__).resolve().parents[2]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def check(ok,code):
    if not ok:raise ValueError(code)
def command(*args):
    subprocess.run(list(map(str,args)),check=True,cwd=ROOT,timeout=180,
                   env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
def execute(out,revision):
    check(re.fullmatch("[a-f0-9]{40}",revision) is not None,"SOURCE_REVISION_INVALID")
    out=Path(out)
    check(out.is_dir() and not out.is_symlink(),"OUTPUT_NOT_ADMITTED")
    original=out/"forward";original.mkdir(mode=0o700)
    render=original/"rendered"
    command(sys.executable,"qualification/walk_w7a/approach_source.py",
            "--profile","forward","--out",original)
    command("xvfb-run","-a",sys.executable,"qualification/walk_w7a/native_approach.py",
            "--profile","forward","--source",original/"source.json","--out",original)
    command(sys.executable,"qualification/walk_w7a/independent_approach.py",original)
    command(sys.executable,"qualification/walk_w16c5a/w4d_liveness.py",original)
    command("xvfb-run","-a",sys.executable,"qualification/walk_w6a/proxy_multiview.py",
            "--source",original,"--out",render)
    for cam in CAMERAS:
        command(sys.executable,"qualification/walk_w6a/qa_video.py",
                "--video",render/(cam+".mp4"),"--out",render/("qa-"+cam))
    command(sys.executable,"qualification/walk_w6a/multiview_rollup.py","--folder",render)
    source=read(original/"source.json")
    receipt=read(original/"source_motion_receipt.json")
    rendered=read(render/"native_render_receipt.json")
    evaluated=read(render/"independent_cross_camera_rollup.json")
    check(source.get("schema")=="scp.walk_w7a_original_approach.v1" and
          source.get("rights")==RIGHTS and source.get("profile")=="forward" and
          source.get("fps_num")==12,"ORIGINAL_SOURCE_OR_RIGHTS_INVALID")
    actor_ids=[x.get("id") for x in source.get("actors",[])]
    check(actor_ids==list(ACTORS) and all(len(x.get("frames",[]))==24 for x in source["actors"]),
          "ORIGINAL_ACTOR_CLOCK_MISMATCH")
    source_sha=sha(original/"source.json")
    glb=original/"original_synthetic_24frame_skinned.glb"
    blend=original/"original_source_grounded_24frame_native.blend"
    check(receipt.get("source_sha256")==source_sha and
          receipt.get("glb_sha256")==sha(glb) and receipt.get("blend_sha256")==sha(blend) and
          receipt.get("frame_count")==24 and receipt.get("fps_num")==12,
          "ORIGINAL_NATIVE_SOURCE_HASH_MISMATCH")
    check(receipt.get("full_body")=="FAIL_ABSTRACT_LIMBS_ONLY" and
          receipt.get("human_anatomy")=="UNKNOWN_NO_INDEPENDENT_JCS_OR_ROM",
          "FIRST_SCIENTIFIC_FAILURE_NOT_RETAINED")
    check(rendered.get("rights")==RIGHTS and rendered.get("source_motion_sha256")==source_sha and
          evaluated.get("source_motion_sha256")==source_sha and
          evaluated.get("status")=="PASS_ALL_REQUIRED_VIEWS_L1_ONLY",
          "ORIGINAL_SOURCE_VIDEO_JOIN_FAIL")
    sources=rendered.get("cameras",[])
    judges=evaluated.get("cameras",[])
    check({x["camera"] for x in sources}==set(CAMERAS) and
          {x["camera"] for x in judges}==set(CAMERAS),"CAMERA_SOURCE_COVERAGE")
    video_sha={}
    for cam in CAMERAS:
        a=next(x for x in sources if x["camera"]==cam)
        b=next(x for x in judges if x["camera"]==cam)
        video_sha[cam]=sha(render/(cam+".mp4"))
        check(a.get("video_sha256")==video_sha[cam] and
              b.get("video_sha256")==video_sha[cam] and
              a.get("frame_count")==24 and b.get("status")=="PASS_L1_VIDEO_ONLY",
              "ORIGINAL_CLEAN_VIDEO_HASH_OR_L1")
    report={
     "schema":SCHEMA,"job_id":"w7a-forward-24","revision":revision,
     "rights":RIGHTS,"source_class":"public-synthetic",
     "source_sha256":source_sha,"glb_sha256":sha(glb),
     "blend_sha256":sha(blend),"video_sha256":video_sha,
     "fps":12,"frames":24,"actor_ids":list(ACTORS),"cameras":list(CAMERAS),
     "observed_video":"PASS_ALL_REQUIRED_VIEWS_L1_ONLY",
     "human_behavior":"FAIL_ABSTRACT_LIMBS_ONLY",
     "human_anatomy":"UNKNOWN_NO_INDEPENDENT_JCS_OR_ROM",
     "release":"HELD_R009_NOT_RUN_NOT_ADMITTED"
    }
    (out/"result.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("ACTUAL_ORIGINAL_SYNTHETIC_NATIVE_JOB_L1_ONLY_WITH_BEHAVIOR_FAIL",revision)
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    p.add_argument("--revision",required=True)
    args=p.parse_args()
    execute(args.out,args.revision)
if __name__=="__main__":main()
