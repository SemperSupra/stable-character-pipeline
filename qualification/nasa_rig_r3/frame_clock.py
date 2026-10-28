"""Sample exact 0-based Blender frames for this source-bound NASA GLB.

The original GLB's animation times are 0, 1, ... 9 seconds. bpy glTF
import anchors source time zero at scene frame zero. This module is deliberately
narrow; MMD VMD import and other assets may have different time conventions.
"""
import math

def source_aligned_frames(sample_count, frames_per_second):
    if (not isinstance(sample_count, int) or isinstance(sample_count, bool)
            or not 2 <= sample_count <= 30):
        raise ValueError("unadmitted sample count")
    if (not isinstance(frames_per_second, (int, float))
            or isinstance(frames_per_second, bool)
            or not math.isfinite(frames_per_second)
            or not 1 <= frames_per_second <= 240):
        raise ValueError("invalid imported scene FPS")
    frames = [int(round(i * frames_per_second)) for i in range(sample_count)]
    if frames[0] != 0 or any(b <= a for a,b in zip(frames, frames[1:])):
        raise ValueError("source time zero or monotonic frames violated")
    return frames
