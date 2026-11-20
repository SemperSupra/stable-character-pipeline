"""Source 60 Hz to retarget 12 fps native timeline matching for 24 Hz probes."""
import math
def original_index(i, source_first=120, original_fps=60, observed_fps=24):
 if not isinstance(i,int) or not 0<=i<143:raise ValueError("SOURCE_SAMPLE_INDEX_BOUNDS")
 return source_first+i*original_fps/observed_fps
def sample_interpolated(fk_at,frame,metric):
 if not math.isfinite(frame) or frame<0 or frame>2399:raise ValueError("SOURCE_FRAME_NOT_BOUNDED")
 low=int(math.floor(frame));high=min(2399,low+1);alpha=frame-low
 a=fk_at(low)[metric];b=fk_at(high)[metric]
 if not all(math.isfinite(x) for x in (*a,*b)):raise ValueError("SOURCE_FK_NONFINITE")
 return tuple((1-alpha)*a[i]+alpha*b[i] for i in range(3))
def near_ground_ratio(source,target):
 a=source.get("near_ground_p50_world_speed_mps")
 b=target.get("near_ground_p50_world_speed_mps")
 if a is None or b is None or a<=0:return None
 return round(b/a,6)
