"""Independent decode-and-measure A/V mux observer.

No reliance on generator's timing calculations, only its frozen fixture grid
and source hashes. Verifies actual decoded audio samples and video pixels,
ffprobe frame PTS, and a separately bounded H.264/AAC mobile candidate.
"""
import hashlib,json,math,pathlib,struct,subprocess,sys,wave
from fractions import Fraction

RATE=48000
WIDTH,HEIGHT=160,90
CLICK=96000
CASES={
 "24":(Fraction(24,1),240,480000,48),
 "30":(Fraction(30,1),300,480000,60),
 "ntsc":(Fraction(30000,1001),300,480480,60),
}
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def command(*args):
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=100)
    if result.returncode:
        raise ValueError("FIRST_FAILURE command "+repr(args)+" "+result.stderr[-1200:].decode(errors="replace"))
    return result.stdout
def probe(path,selection):
    return json.loads(command("ffprobe","-hide_banner","-loglevel","error",
       "-select_streams",selection,"-show_streams","-show_frames",
       "-show_entries","stream=codec_type,codec_name,sample_rate,channels,width,height,start_time,time_base:frame=media_type,best_effort_timestamp_time",
       "-of","json",str(path)))
def source_wav(path,expected):
    with wave.open(str(path),"rb") as w:
        if (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())!=(1,2,RATE,expected):
            raise ValueError("not exact mono original 48k PCM16")
        raw=w.readframes(expected)
    if len(raw)!=expected*2:raise ValueError("truncated original WAV")
    for sample in (0,1,255,CLICK-1,CLICK,CLICK+1,expected-1):
        x=struct.unpack_from("<h",raw,sample*2)[0]
        if x!=(20000 if sample==CLICK else 0):raise ValueError("original source is not synthetic one-click")
    return raw
def decode_audio(path):
    return command("ffmpeg","-hide_banner","-loglevel","error","-nostdin",
       "-i",str(path),"-map","0:a:0","-ac","1","-ar",str(RATE),
       "-acodec","pcm_s16le","-f","s16le","-")
def peak_sample(raw):
    if len(raw)%2:raise ValueError("truncated PCM decoded audio")
    values=memoryview(raw).cast("h")
    return max(range(len(values)),key=lambda i:abs(values[i])),max(abs(x) for x in values)
def decode_video(path,n):
    buf=command("ffmpeg","-hide_banner","-loglevel","error","-nostdin",
       "-i",str(path),"-map","0:v:0","-pix_fmt","gray","-f","rawvideo","-")
    one=WIDTH*HEIGHT
    if len(buf)!=one*n:raise ValueError(f"wrong decoded video frames {len(buf)} expected {one*n}")
    # Decode every frame and require *exactly one* original white marker.
    counts=[]
    for i in range(n):
        frame=buf[i*one:(i+1)*one]
        if sum(frame)/one>128:counts.append(i)
    return counts
def inspect(root):
    root=pathlib.Path(root)
    m=json.loads((root/"native_source_manifest.json").read_text())
    if (m["schema"]!="spatial_audio.avsync_native_fixture.v1" or
        m["rights"]!="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC" or
        m["sample_rate"]!=RATE or m["width"]!=WIDTH or m["height"]!=HEIGHT or
        m["click_sample"]!=CLICK):
        raise ValueError("wrong experiment/source custody")
    found={}
    for case in m["cases"]:
        name=case["id"]
        if name not in CASES or name in found:raise ValueError("duplicate/unqualified media")
        fps,vn,an,flash=CASES[name]
        if (str(case["rate"]) != ("30000/1001" if name=="ntsc" else name)
            or case["video_frames"]!=vn or case["audio_frames"]!=an or case["flash_frame"]!=flash):
            raise ValueError("planned frame/sample size changed")
        src=root/(name+".wav")
        master=root/(name+"_master.mkv")
        mobile=root/(name+"_mobile.mp4")
        for p,expectedsha in [(src,case["original_pcm_wav_sha256"]),
                              (master,case["lossless_master_sha256"]),
                              (mobile,case["mobile_preview_sha256"])]:
            if sha(p)!=expectedsha:raise ValueError("original asset SHA mismatch")
        reference=source_wav(src,an)
        original=decode_audio(master)
        if original!=reference:raise ValueError("lossless mux changed a sample or frame count")
        clicked,amp=peak_sample(original)
        if clicked!=CLICK or amp!=20000:raise ValueError("click not at exact 2-sec sample")
        mkvframes=decode_video(master,vn)
        if mkvframes!=[flash]:raise ValueError("lossless visual marker at wrong video frame")
        pv=probe(master,"v:0")
        pa=probe(master,"a:0")
        if len(pv["streams"])!=1 or len(pa["streams"])!=1:raise ValueError("missing streams")
        vs=pv["streams"][0];ass=pa["streams"][0]
        if (vs["codec_name"]!="ffv1" or vs["width"]!=WIDTH or vs["height"]!=HEIGHT
            or ass["codec_name"]!="pcm_s16le" or int(ass["sample_rate"])!=RATE):
            raise ValueError("wrong actual native codecs")
        vframes=[f for f in pv["frames"] if f["media_type"]=="video"]
        if len(vframes)!=vn:raise ValueError("ffprobe wrong video-frame count")
        timestamp_errors=[]
        for i,f in enumerate(vframes):
            actual=Fraction(f["best_effort_timestamp_time"])
            wanted=Fraction(i,1)/fps
            error=abs(float(actual-wanted))
            if error>0.0011:raise ValueError(f"mux video PTS drift frame={i} error={error}")
            timestamp_errors.append(error)
        clicktime=Fraction(CLICK,RATE)
        flashtime=Fraction(vframes[flash]["best_effort_timestamp_time"])
        if abs(float(flashtime-clicktime))>0.5/float(fps)+0.0011:
            raise ValueError("visual flash is more than half a video frame from audio click")
        decodedmobile=decode_audio(mobile)
        mobile_at,amobile=peak_sample(decodedmobile)
        if abs(mobile_at-CLICK)>1024:raise ValueError("AAC codec priming moved audio outside bounded window")
        mp4frames=decode_video(mobile,vn)
        if mp4frames!=[flash]:raise ValueError("mobile flash moved during H264 encode")
        mv=probe(mobile,"v:0")["streams"][0]
        ma=probe(mobile,"a:0")["streams"][0]
        if mv["codec_name"]!="h264" or ma["codec_name"]!="aac":raise ValueError("not H264/AAC mobile candidate")
        found[name]=dict(fps=f"{fps.numerator}/{fps.denominator}",frames=vn,audio_frames=an,
         master_start_video_pts=vframes[0]["best_effort_timestamp_time"],
         flash_frame=flash,flash_pts_seconds=float(flashtime),
         click_exact_sample=clicked,click_seconds=float(clicktime),
         max_video_pts_error_seconds=max(timestamp_errors),
         lossless_decoded_pcm_sha256=hashlib.sha256(original).hexdigest(),
         lossless_master_sha256=sha(master),
         mobile_peak_sample=mobile_at,mobile_click_difference_samples=mobile_at-CLICK,
         mobile_codec="H264_AAC_CANDIDATE_NOT_DEVICE_ACCEPTED",mobile_sha256=sha(mobile))
    if set(found)!=set(CASES):raise ValueError("missing 3-case media matrix")
    return dict(schema="spatial_audio.avsync_mux_verification.v1",
                status="PASS_LOSSLESS_AND_MOBILE_CANDIDATE",
                source_rights=m["rights"],ffmpeg_version=m["ffmpeg_version"],
                ffprobe_version=m["ffprobe_version"],
                lossless_click_sample_tolerance=0,
                lossless_video_pts_max_tolerance_seconds=0.0011,
                mobile_aac_click_tolerance_samples=1024,
                cases=found,
                excluded=["REAL_PERSON_AUDIO","HUMAN_LIPSYNC","AUDIO_HARDWARE_LATENCY",
                  "IPHONE_AUDITION","PERSONALIZED_HRTF","VARIABLE_FRAME_RATE",
                  "CODEC_DELAY_COMPENSATION_IN_ALL_TARGETS"])
if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: inspect_avsync.py NATIVE_DIR RECEIPT.json")
    try:
        result=inspect(sys.argv[1])
    except Exception as e:
        result={"schema":"spatial_audio.avsync_mux_verification.v1","status":"FAIL","first_failure":str(e)}
        pathlib.Path(sys.argv[2]).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        print("AVSYNC_MUX_OBSERVER_FIRST_FAILURE",str(e),file=sys.stderr)
        raise
    pathlib.Path(sys.argv[2]).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("AVSYNC_MUX_INDEPENDENT_NATIVE_PCM_VIDEO_PASS cases",len(result["cases"]),
          "max_pts_error",max(x["max_video_pts_error_seconds"] for x in result["cases"].values()))
