#!/usr/bin/env python3
"""Original synthetic native Csound PCM -> FFmpeg H264/PCM. NOT historical choreography/real motion."""
import array, hashlib, json, math, subprocess, sys, wave
from pathlib import Path
SAMPLE_RATE, FPS, W, H=48000,12,160,96
PROJECT="0e7e1752427569a97e293cb974258db4071e52f3274adfde75fff9cfe706465c"
class Reject(Exception):pass
def run(cmd,stdin=None):
    p=subprocess.run(cmd,input=stdin,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode:raise Reject("native command failed: "+str(cmd[0])+" "+p.stderr[-1000:].decode(errors="replace"))
    return p.stdout
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(root):
    r=json.loads((root/"receipt.json").read_text());t=json.loads((root/"time-map.json").read_text())
    if r.get("source_project_sha256")!=PROJECT or t.get("source_audio_project_sha256")!=PROJECT:raise Reject("source project substitution")
    if r.get("sample_rate_hz")!=48000 or r.get("sample_count")!=896000 or t.get("proposed_score_end_samples")!="896000" or t.get("original_source_audio_end_samples")!="768000" or t.get("score_minus_audio_end_samples")!="128000":raise Reject("source-versus-proposed clock divergence erased")
    n=r.get("note_onsets",[])
    if len(n)!=20 or not all(isinstance(x.get("sample"),int) for x in n):raise Reject("missing typed 20 note onsets")
    return [x["sample"] for x in n]
def pcm(path):
    with wave.open(str(path),"rb") as w:
        if (w.getnchannels(),w.getsampwidth(),w.getframerate())!=(1,2,SAMPLE_RATE):raise Reject("PCM format invalid")
        count=w.getnframes();raw=w.readframes(count)
    a=array.array("h");a.frombytes(raw)
    if sys.byteorder!="little":a.byteswap()
    starts=[i for i,x in enumerate(a) if x>18000 and (i==0 or a[i-1]<=18000)]
    return count,raw,starts
def frame(i,n,markers):
    # Two moving ORIGINAL ABSTRACT PROXIES, not body rigs, gait, dance or real-person footage.
    out=bytearray(W*H*3)
    xa=20+i*34//(n-1);xb=124-i*34//(n-1)
    for y in range(H):
        for x in range(W):
            offset=3*(y*W+x)
            if i in markers and x<12 and y<12:out[offset:offset+3]=b"\xff\xff\xff"
            elif xa<=x<xa+12 and 35<=y<59:out[offset:offset+3]=b"\xed\x40\x30"
            elif xb<=x<xb+12 and 35<=y<59:out[offset:offset+3]=b"\x40\x75\xef"
    return out
def synth(root):
    onsets=load(root);count,raw,observed=pcm(root/"csound-target.wav")
    if count!=896000 or len(observed)!=20 or max(abs(x-y) for x,y in zip(onsets,observed))>2:raise Reject("real native PCM onset mismatch")
    if any(s%4000 for s in observed):raise Reject("not exact-on-frame at 12fps")
    marks={s//4000 for s in observed}
    if len(marks)!=20:raise Reject("onset alias")
    mp4=root/"original-synthetic-proxy-h264.mp4";mkv=root/"original-synthetic-native-av.mkv"
    if mp4.exists() or mkv.exists():raise Reject("refuse overwrite")
    cmd=["ffmpeg","-v","error","-f","rawvideo","-pixel_format","rgb24","-video_size",f"{W}x{H}","-framerate","12","-i","pipe:0","-c:v","libx264","-preset","veryfast","-threads","2","-pix_fmt","yuv420p",str(mp4)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for i in range(224):p.stdin.write(frame(i,224,marks))
        p.stdin.close();err=p.stderr.read();status=p.wait()
    except Exception:
        p.kill();p.wait();raise
    if status:raise Reject("FFmpeg encode "+err[-1000:].decode(errors="replace"))
    run(["ffmpeg","-v","error","-i",str(mp4),"-i",str(root/"csound-target.wav"),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","pcm_s16le","-shortest",str(mkv)])
def observe(root,video=None,onset_shift=0):
    original=load(root);count,raw,onsets=pcm(root/"csound-target.wav")
    if count!=896000 or len(onsets)!=20 or max(abs(x-y) for x,y in zip(onsets,original))>2:raise Reject("native PCM differs from source oracle")
    if onset_shift:onsets=[x+onset_shift for x in onsets]
    src=video or root/"original-synthetic-native-av.mkv"
    entries=json.loads(run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","frame=best_effort_timestamp_time","-of","json",str(src)])).decode()).get("frames",[])
    if len(entries)!=224:raise Reject("frame dropped/duplicated/truncated")
    times=[float(e["best_effort_timestamp_time"]) for e in entries]
    tolerance=.000501 if src.suffix==".mkv" else .00001
    if any(not math.isfinite(v) or abs(v-i/FPS)>tolerance for i,v in enumerate(times)):raise Reject("PTS disagrees with source 12fps clock")
    # Matroska defaults to millisecond timebase (max 0.3334ms quantization), not exact fractions.
    if src.suffix==".mkv":
        native=run(["ffmpeg","-v","error","-i",str(src),"-map","0:a:0","-f","s16le","-ac","1","-ar","48000","pipe:1"])
        if native!=raw:raise Reject("native mux PCM not byte-identical")
    video_pixels=run(["ffmpeg","-v","error","-i",str(src),"-map","0:v:0","-f","rawvideo","-pix_fmt","rgb24","pipe:1"])
    if len(video_pixels)!=224*W*H*3:raise Reject("decoded pixel count not full")
    marked=[]
    centroids=[]
    for i in range(224):
        v=memoryview(video_pixels)[i*W*H*3:(i+1)*W*H*3]
        if sum(v[(y*W+x)*3] for y in range(8) for x in range(8))/64>220:marked.append(i)
        if i in (0,223):
            rr=[];bb=[]
            for x in range(W):
                r,g,b=v[(46*W+x)*3:(46*W+x)*3+3]
                if r>g+45 and r>b+45:rr.append(x)
                if b>g+40 and b>r+40:bb.append(x)
            if len(rr)<4 or len(bb)<4:raise Reject("two proxy actors not decoded")
            centroids.append((sum(rr)/len(rr),sum(bb)/len(bb)))
    expected=[(s+2000)//4000 for s in onsets]
    if marked!=expected:raise Reject("native decoded visual events not aligned with observed PCM onsets")
    if centroids[0][1]-centroids[0][0]<centroids[1][1]-centroids[1][0]+50:raise Reject("two proxy motions not decoded")
    return {"schema":"scp.original-synthetic-native-av-pts.v0","source_project_sha256":PROJECT,"actual_frames":224,"video_fps":"12/1","actual_pcm_samples":count,"audio_note_onsets":len(onsets),"visual_markers":len(marked),"maximum_frame_pts_error_seconds":max(abs(v-i/12) for i,v in enumerate(times)),"max_audio_visual_marker_frame_error":0,"original_pcm_sha256":sha(root/"csound-target.wav"),"mux_sha256":sha(src),"original_mux_pcm_byte_match":src.suffix==".mkv","proxy_centroids_first_last":centroids,"status":"PASS_ORIGINAL_SYNTHETIC_NATIVE_PCM_H264_PTS_ONLY","historical_score":"NOT_ADMITTED","real_measured_choreography":"NOT_RUN","anatomy_contact_identity":"UNKNOWN","R009":"HELD_NOT_ACCEPTED"}
def main(root):
    synth(root)
    result=observe(root)
    try:observe(root,onset_shift=4000)
    except Reject:pass
    else:raise Reject("false accept of one-frame PCM-to-video offset")
    clip=root/"original-synthetic-truncated-control.mp4"
    run(["ffmpeg","-v","error","-i",str(root/"original-synthetic-proxy-h264.mp4"),"-frames:v","223","-an",str(clip)])
    try:observe(root,video=clip)
    except Reject:pass
    else:raise Reject("false accept of truncated video")
    result["negative_controls"]={"one_frame_audio_offset":"REJECTED","truncated_video":"REJECTED"}
    (root/"av-pts-evidence.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":
    try:
        if len(sys.argv)!=2:raise Reject("usage: python3 native_av_pts.py original-score-evidence-dir")
        main(Path(sys.argv[1]))
    except (Reject,ValueError,KeyError) as e:
        print("FAIL_CLOSED",str(e),file=sys.stderr);sys.exit(1)
