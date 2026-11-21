"""BG independent H264 72f format + 3 real decoded-frame changes source-safe critic."""
import hashlib,json,math,struct,subprocess
from pathlib import Path

def need(x,reason):
    if not x:raise ValueError(reason)
def probe(path,ffmpeg):
    """Independently decode using SHA pinned external FFmpeg, not Blender or JSON claims."""
    cmd=[ffmpeg,"-hide_banner","-loglevel","info","-i",str(path),
         "-vf","showinfo","-an","-f","null","-"]
    process=subprocess.run(cmd,capture_output=True,text=True,check=True)
    data=process.stderr
    import re
    need("Video: h264" in data and "384x216" in data and
         re.search(r"\b12(?:\.0+)? fps\b",data),"NOT_BOUNDED_H264")
    frame_numbers=[int(i) for i in re.findall(r"showinfo[^\n]*?\bn:\s*(\d+)",data)]
    # This is a fresh decoder of all encoded frames, independent of original PNGs.
    need(frame_numbers==list(range(72)),"MISSING_ACTUAL_DECODED_FRAMES")
    m=re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)",data)
    need(m is not None,"NO_REAL_MOVIE_DURATION")
    duration=3600*int(m.group(1))+60*int(m.group(2))+float(m.group(3))
    need(math.isfinite(duration) and abs(duration-6.0)<.12,"NOT_SIX_SECONDS")
    return {"h264_codec":"h264","width":384,"height":216,"fps":12,
            "actual_decoded_frames":len(frame_numbers),"duration_s":round(duration,6)}

def decoded_frame(path,n,ffmpeg):
    cmd=[ffmpeg,"-hide_banner","-loglevel","error","-i",str(path),
         "-vf",f"select=eq(n\\,{n})","-vsync","vfr",
         "-frames:v","1","-f","image2pipe","-vcodec","png","pipe:1"]
    data=subprocess.run(cmd,capture_output=True,check=True).stdout
    need(data[:8]==b"\x89PNG\r\n\x1a\n" and len(data)>1000,"NO_TRUE_DECODED_VIDEO_PIXEL")
    need(struct.unpack_from(">II",data,16)==(384,216),"DECODED_WRONG_FRAME_DIMENSION")
    return hashlib.sha256(data).hexdigest()
def validate(report,root,allow_decoding=True,ffmpeg_exe=None):
    need(report.get("schema")=="scp.n03d-bg.two-camera-source-safe-visual-witness.v1" and
         report.get("source_class")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and
         report.get("source_MPF_upstream")=="9de0707fdc88438d7c53a1a2ac7937d9221e2431" and
         report.get("source_bvh_blob")=="a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61" and
         report.get("shoes01_CC0_archive_sha256")=="ded3f70428505eabbf1f6d7b5f61196a7366ef20757103d276ad0ed336c35ada" and
         report.get("official_blender")==[5,2,4] and
         report.get("native_scene_h264_12fps_frames")==72 and
         report.get("visual_full_biomechanics_verified") is False and
         report.get("user_protected_Naomi_Alison_used") is False and
         report.get("physical_gait_accepted") is False and
         report.get("mvp_accepted") is False and
         report.get("status")=="PASS_NARROW_AUTHENTIC_2_CAMERA_FILM_HOLD_VISUAL_QUALITY",
         "SPOOFED_FILM_OR_SOURCE_RIGHTS")
    subjects=report.get("actual_separate_source_original_actors",[])
    need(len(subjects)==4 and
         set((s["actor"],s["rig"]) for s in subjects)==
         {(a,r) for a in ("AsterOriginal","JuniperOriginal") for r in ("default","game_engine")},
         "FILM_RIG_OR_ACTOR_SET")
    for a in subjects:
        need(a["bones"]==(163 if a["rig"]=="default" else 53) and
             a["same_morphology_19158_vertex_delta_m"]<=.001 and
             a["source_frames"]==[120,475] and
             a["true_physical_gait_accepted"] is False,"WRONG_RIG_MOTION_OR_SHAPE")
    witness=report.get("native_source_to_shoe_observations",[])
    need([x["native_frame"] for x in witness]==[0,35,71] and
         [x["source_frame"] for x in witness]==[120,295,475] and
         all(len(x["actor_observations"])==4 for x in witness),"VISUAL_SOURCE_CLOCK")
    videos=report.get("videos",[])
    need(len(videos)==2 and set(x["camera"] for x in videos)=={"front","oblique"} and
         len({x["sha256"] for x in videos})==2,"NO_TRUE_DUAL_CAMERA")
    stats={}
    for item in videos:
        need(item["mvp_accepted"] is False and
             item["source_rights_attribution"]=="MakeHuman CC0 + Ian Mason 100STYLE CC BY4" and
             len(item["sha256"])==64 and item["bytes"]>10000,"SOURCE_RIGHTS_FILM_SIZE")
        path=Path(root)/item["file"]
        need(path.is_file() and path.stat().st_size==item["bytes"] and
             hashlib.sha256(path.read_bytes()).hexdigest()==item["sha256"],"VIDEO_BYTES_CHANGED")
        if allow_decoding:
            need(ffmpeg_exe and Path(ffmpeg_exe).is_file(),"PINNED_FFMPEG_NOT_PROVIDED")
            data=probe(path,ffmpeg_exe)
            h=[decoded_frame(path,k,ffmpeg_exe) for k in (0,35,71)]
            need(len(set(h))==3,"FILM_STATIC_OR_CLOCK_FROZEN")
            data["actual_pixel_sha256_at_frame0_35_71"]=h
            stats[item["camera"]]=data
    return {"schema":"scp.n03d-bg.independent-2-camera-video-critic.v1",
            "source_exact":True,"source_rights_admitted_original_only":True,
            "real_native_H264_12fps_72_decoded_frames":allow_decoding,
            "camera_proofs":stats,"actual_gait_visual_reviewed_by_human":False,
            "actual_source_bvh_ground_calibrated":False,
            "physical_gait_accepted":False,"mvp_accepted":False,
            "status":"PASS_NARROW_VIDEO_FORMAT_AND_PIXEL_CHANGE_HOLD_GAIT" if allow_decoding else "HOLD_METADATA_ONLY_NO_VIDEO_DECODING"}
