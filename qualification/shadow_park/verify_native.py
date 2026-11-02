#!/usr/bin/env python3
"""Independent decoded H264/PNG, source hash and Blender-native receipt reviewer.
Full video is still NOT genuine gait, anatomy, human likeness or CPE acceptance.
"""
import argparse,hashlib,json,pathlib,subprocess,math
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def decoded(path):
 result=subprocess.run(["ffprobe","-v","error","-count_frames","-select_streams","v:0",
   "-show_entries","stream=nb_read_frames,codec_name,pix_fmt,width,height,avg_frame_rate",
   "-of","json",str(path)],capture_output=True,text=True,check=True)
 streams=json.loads(result.stdout)["streams"]
 if len(streams)!=1:raise AssertionError("WRONG_NUMBER_OF_VIDEO_STREAMS")
 s=streams[0]
 if s.get("codec_name")!="h264" or s.get("pix_fmt")!="yuv420p" or s.get("width")!=480 or s.get("height")!=270 or s.get("avg_frame_rate")!="12/1" or int(s.get("nb_read_frames",0))!=72:
  raise AssertionError("NATIVE_H264_FRAME_OR_IOS_FORMAT_MISMATCH:"+str(s))
 return {"sha256":sha(path),"frames_decoded":72,"codec":"h264","pixel_format":"yuv420p",
   "width":480,"height":270,"fps":12,"bytes":path.stat().st_size}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--root",required=True)
 p.add_argument("--out",required=True)
 a=p.parse_args();root=pathlib.Path(a.root)
 trace_path=root/"trace.json"
 trace=json.loads(trace_path.read_text())
 source_sha=sha(trace_path)
 qa=json.loads((root/"review-baseline.json").read_text())
 native=json.loads((root/"native"/"native_receipt.json").read_text())
 assert qa["status"]=="PASS_SYNTHETIC_GROUNDTRUTH_ENGINEERING_ONLY"
 assert qa["review_passed"] is True and qa["source_sha256"]==source_sha
 assert native["status"]=="PASS_PUBLIC_ORIGINAL_SYNTHETIC_SKIN_AND_2CAMERA_RENDER_ONLY"
 assert native["trace_sha256"]==source_sha
 assert native["actors"]==["CobaltOriginal","MarigoldOriginal"]
 assert native["actual_armature_modifiers"]==26
 assert native["proxy_meshes"]==26
 assert native["articulated_segments_per_actor"]==13
 assert len(native["actual_skinned_moving_samples"])==10
 assert all(math.isfinite(v) and v>.035 for v in native["actual_skinned_moving_samples"].values())
 assert native["maximum_source_to_bpy_head_m"]<.002
 assert native["maximum_source_to_bpy_tail_m"]<.002
 assert native["true_hierarchical_ik"]=="NOT_RUN_UNPARENTED_PROXY_CONTROLS"
 assert native["human_identity"]=="NOT_VERIFIED"
 assert native["private_r009"]=="HELD_NOT_ACCEPTED"
 media={}
 for view in ("front","oblique"):
  pngs=sorted((root/"native"/view).glob("frame_*.png"))
  assert len(pngs)==72,(view,len(pngs))
  assert len({sha(pngs[n]) for n in (0,12,24,36,48,60,71)})>=5,"STATIC_VIDEO_FALSE_ACCEPT"
  media[view]=decoded(root/(view+".mp4"))
 assert media["front"]["sha256"]!=media["oblique"]["sha256"],"FALSE_MULTI_CAMERA_VIDEO_ALIAS"
 contact=root/"contact-sheet.png"
 assert contact.stat().st_size>1000
 report={
  "schema":"scp.shadow.two-view-native-independent.v1",
  "status":"PASS_SYNTHETIC_72F_2ACTOR_2CAMERA_NATIVE_H264_ONLY",
  "trace_sha256":source_sha,"native_receipt_sha256":sha(root/"native"/"native_receipt.json"),
  "camera_media":media,"contact_sheet_sha256":sha(contact),
  "source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
  "actual_actor_identity":"NOT_VERIFIED",
  "real_human_mocap":"NOT_ADMITTED",
  "biophysical_rom":"UNKNOWN_NOT_INDEPENDENTLY_MEASURED",
  "true_hierarchical_ik":"NOT_RUN",
  "protected_r009":"HELD_NOT_ACCEPTED",
  "CPE":"NOT_PROMOTED"}
 with pathlib.Path(a.out).open("x",encoding="utf-8") as f:
  json.dump(report,f,indent=2,sort_keys=True);f.write("\n")
 print(json.dumps(report,sort_keys=True))
if __name__=="__main__":main()
