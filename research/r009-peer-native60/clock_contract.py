"""Small independent 60Hz key-time oracle. No Blender or protected assets."""
import math

def validate(times,fps=60.0):
    if type(fps) not in (int,float) or not math.isfinite(fps) or fps!=60.0:
        raise ValueError("FPS_NOT_60")
    if not isinstance(times,(list,tuple)) or len(times)!=360:
        raise ValueError("MISSING_OR_EXTRA_SOURCE_TIMESTAMPS")
    if any(type(t) not in (int,float) or not math.isfinite(t) for t in times):
        raise ValueError("NONFINITE_NATIVE_FRAME")
    if abs(times[0])>1e-4 and abs(times[0]-1.0)>1e-4:
        raise ValueError("SOURCE_TARGET_INDEX_ORIGIN")
    if any(abs((times[i]-times[0])-i)>1e-4 for i in range(360)):
        raise ValueError("SOURCE_TARGET_FRAME_GAPS")
    duration=(times[-1]-times[0])/fps
    if abs(duration-359/60)>1e-7:
        raise ValueError("SOURCE_DURATION")
    return {"source_frames":360,"target_frames":360,"fps":60.0,
            "last_source_sample_time_s":round(duration,9),
            "video_duration_seconds":360/60.0,
            "tail_sample_indices":[356,357,358,359],
            "status":"HOLD_NATIVE_KEYS_ONLY"}
