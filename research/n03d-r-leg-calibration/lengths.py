"""N03D-R source v target limb segment length ratios with finite strict verification."""
import math,statistics
def segment(a,b):
 if not isinstance(a,(tuple,list)) or not isinstance(b,(tuple,list)) or len(a)!=3 or len(b)!=3:raise ValueError("SEGMENT_POINT_SHAPE")
 if not all(type(x) in (float,int) and math.isfinite(x) for x in (*a,*b)):raise ValueError("NONFINITE_SEGMENT")
 length=math.dist(a,b)
 if not 1e-6<length<10:raise ValueError("SEGMENT_NOT_PHYSICAL_BOUNDS")
 return length
def compare_lengths(source,target):
 if set(source)!=set(target) or set(source)!={"thigh","shin","foot"}:raise ValueError("SEGMENT_LABEL_MISMATCH")
 ratios={}
 for key in source:
  s,t=source[key],target[key]
  if not all(type(x) in (float,int) and math.isfinite(x) and 1e-6<x<10 for x in (s,t)):
   raise ValueError("NONFINITE_OR_ZERO_LENGTH")
  ratios[key]=t/s
 raw=list(ratios.values())
 median=statistics.median(raw)
 return {"target_to_source_length_ratios":{k:round(v,6) for k,v in ratios.items()},
  "median_length_ratio":round(median,6),"max_min_ratio_spread":round(max(raw)/min(raw),6),
  "uniform_isotropic_scale_proven":False,"calibrated_joint_axes_proven":False,
  "contact_accepted":False}
