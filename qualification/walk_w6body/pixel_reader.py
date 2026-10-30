"""Independent original source full-body multiview H264 decoded pixel diagnostic."""
import hashlib,json,statistics,struct,subprocess,sys
from pathlib import Path
W,H=400,240
def call(args):return subprocess.check_output(args,stderr=subprocess.PIPE)
def run(folder):
 p=Path(folder);r=json.loads((p/"multiview_render_receipt.json").read_text())
 if r["source_rights"]!="ORIGINAL_SELF_AUTHORED_SYNTHETIC" or hashlib.sha256((p/"source.json").read_bytes()).hexdigest()!=r["source_sha256"]:raise ValueError("SOURCE_RIGHTS_OR_HASH")
 if set(r["views"])!={"front","oblique"}:raise ValueError("CAMERA_COVERAGE")
 results={}
 for name in ("front","oblique"):
  v=p/("original_"+name+"_surrogate.mp4")
  if hashlib.sha256(v.read_bytes()).hexdigest()!=r["views"][name]["sha256"]:raise ValueError("VIDEO_HASH")
  info=json.loads(call(["ffprobe","-v","error","-show_streams","-of","json",str(v)]))["streams"]
  video=[x for x in info if x["codec_type"]=="video"]
  if len(video)!=1 or video[0]["codec_name"]!="h264" or video[0]["r_frame_rate"]!="12/1" or (video[0]["width"],video[0]["height"])!=(W,H):raise ValueError("VIDEO_CODEC")
  decoded=call(["ffmpeg","-v","error","-i",str(v),"-map","0:v:0","-pix_fmt","rgb24","-f","rawvideo","-"])
  n=W*H*3
  if len(decoded)!=n*24:raise ValueError("FRAME_COUNT")
  frames=[decoded[n*i:n*(i+1)] for i in range(24)]
  hashes=[hashlib.sha256(f).hexdigest() for f in frames]
  if len(set(hashes))<3:raise ValueError("FRAME_LIVENESS")
  fraction=[sum(a!=b for a,b in zip(x[::3],y[::3]))/(W*H) for x,y in zip(frames,frames[1:])]
  for e in r["source_projection"][name]:
   if len(e["actors"])!=2 or any(not (.24<a["source_projected_height_fraction"]<.88) for a in e["actors"]):raise ValueError("CAMERA_FRAMING")
  results[name]={"unique_decoded_frame_hashes":len(set(hashes)),"median_changed_pixel_fraction":statistics.median(fraction),"same_frame_intervals":sum(x==y for x,y in zip(hashes,hashes[1:])),"video_sha256":r["views"][name]["sha256"]}
 glb=(p/"original_two_actor_fullbody_surrogate.glb").read_bytes()
 if hashlib.sha256(glb).hexdigest()!=r["glb_sha256"] or glb[:4]!=b"glTF" or struct.unpack_from("<I",glb,8)[0]!=len(glb):raise ValueError("GLTF_HASH_OR_HEADER")
 n,t=struct.unpack_from("<II",glb,12)
 if t!=0x4e4f534a:raise ValueError("GLTF_JSON")
 g=json.loads(glb[20:20+n])
 if len(g.get("skins",[]))!=2 or len(g.get("meshes",[]))<14:raise ValueError("FULL_BODY_MESH_COUNT")
 z={"schema":"scp.walk_w6_original_multiview_pixels.v1","status":"PASS_GEOMETRIC_SURROGATE_TWO_CAMERA_NATIVE_DECODE_ONLY","profile":r["profile"],"views":results,"source_sha256":r["source_sha256"],"mesh_count":len(g["meshes"]),"human_visual_model":"NOT_RUN_UNKNOWN","original_l1":"RED_NOT_REASSESSED","scope":"NOT_REAL_PERSON_OR_ANATOMICAL_ACCEPTANCE"}
 (p/"decoded_receipt.json").write_text(json.dumps(z,indent=2,sort_keys=True)+"\n")
 print("W6_SURROGATE_MULTICAMERA_DECODE_PASS",r["profile"],results)
if __name__=="__main__":run(sys.argv[1])
