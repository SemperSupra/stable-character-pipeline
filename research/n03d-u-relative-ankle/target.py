"""Bounded source-hip-relative ankle targets for exact native five-bone IK experiments."""
import math
def finite3(p):
 return isinstance(p,(tuple,list)) and len(p)==3 and all(type(x) in (int,float) and math.isfinite(x) for x in p)
def target(source_hip,source_ankle,native_hip,scale,yaw):
 if not all(finite3(x) for x in (source_hip,source_ankle,native_hip)):raise ValueError("NONFINITE_SOURCE_LANDMARK")
 if type(scale) not in (int,float) or not .3<=scale<=2. or not math.isfinite(yaw):raise ValueError("SOURCE_MORPHOLOGY_SCALE")
 c,s=math.cos(yaw),math.sin(yaw)
 # BVH (X,Z horizontal and Y up) -> native Blender (X,Y horizontal, Z up).
 dx=(source_ankle[0]-source_hip[0])*scale
 dy=(source_ankle[2]-source_hip[2])*scale
 dz=(source_ankle[1]-source_hip[1])*scale
 return (native_hip[0]+c*dx-s*dy,native_hip[1]+s*dx+c*dy,native_hip[2]+dz)
def bounded_delta(current,desired,max_step=.04):
 if not finite3(current) or not finite3(desired):raise ValueError("NONFINITE_ANKLE_TARGET")
 if type(max_step) not in (int,float) or not math.isfinite(max_step) or not 0<max_step<=.05:
  raise ValueError("BAD_CORRECTION_BOUND")
 delta=[float(b-a) for a,b in zip(current,desired)]
 length=math.sqrt(sum(x*x for x in delta))
 f=min(1.,max_step/max(length,1e-12))
 return tuple(f*x for x in delta)
def reachability(hip,ankle,thigh_m,shin_m):
 if not finite3(hip) or not finite3(ankle):raise ValueError("BAD_POSE_POINT")
 if any(type(x) not in (float,int) or not math.isfinite(x) or x<=0 for x in (thigh_m,shin_m)):raise ValueError("BAD_REST_LIMB")
 length=math.dist(hip,ankle)
 lower=abs(thigh_m-shin_m)
 upper=thigh_m+shin_m
 return {"hip_to_ankle_m":round(length,6),"lower_reach_m":round(lower,6),
  "upper_reach_m":round(upper,6),"two_segment_reachable":lower-1e-9<=length<=upper+1e-9,
  "joint_axes_and_pole_calibrated":False,"foot_plant_accepted":False}
