"""Original exact rational 48k sample to 12/24/30/30000:1001 video clock.
No source time inferred from an untimed rig. No universal audio latency constants.
"""
from dataclasses import dataclass
from math import gcd
RIGHTS="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC"
MAX_TICK=(1<<63)-1
SUPPORTED={(12,1),(24,1),(30,1),(30000,1001)}
@dataclass(frozen=True)
class Clock:
    fps_num:int
    fps_den:int
    audio_hz:int=48000
    rights:str=RIGHTS
    def check(self):
        if self.rights!=RIGHTS or (type(self.fps_num),type(self.fps_den),type(self.audio_hz))!=(int,int,int):
            raise ValueError("RIGHTS_OR_CLOCK_TYPE")
        if (self.fps_num,self.fps_den) not in SUPPORTED or self.audio_hz!=48000:
            raise ValueError("CLOCK_NOT_SOURCE_ADMITTED")
    def frame(self,sample):
        self.check()
        if type(sample)is not int or not 0<=sample<=MAX_TICK:raise ValueError("SOURCE_SAMPLE_NON_INT64")
        return (sample*self.fps_num)//(self.audio_hz*self.fps_den)
    def start(self,frame):
        self.check()
        if type(frame)is not int or not 0<=frame<=MAX_TICK:raise ValueError("SOURCE_FRAME_NON_INT64")
        numerator=frame*self.audio_hz*self.fps_den
        return (numerator+self.fps_num-1)//self.fps_num
def reject_collapse(a,b,clock):
    clock.check()
    if type(a)is not int or type(b)is not int or not 0<=a<b<=MAX_TICK:raise ValueError("NONINCREASING_SOURCE_TIMESTAMP")
    # Different source samples can quantize to the same visual frame, but MUST
    # never be rewritten as identical source events or interpolated using float.
    return {"strict_source_order":True,"same_display_frame":clock.frame(a)==clock.frame(b),
            "source_sample_delta":b-a,"first_frame":clock.frame(a),"last_frame":clock.frame(b)}
def packet(clock,events):
    clock.check();prior=-1;out=[]
    for item in events:
        if item.get("rights")!=RIGHTS or item.get("kind")!="SOURCE_ANNOTATED_EVENT":
            raise ValueError("SOURCE_RIGHTS_OR_EVENT_CLASS")
        s=item.get("sample")
        if type(s)is not int or not 0<=s<=MAX_TICK or s<=prior:raise ValueError("SOURCE_EVENT_ORDER")
        prior=s
        out.append({"sample":s,"frame":clock.frame(s),"frame_start_sample":clock.start(clock.frame(s))})
    return out
