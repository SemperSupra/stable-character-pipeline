"""Compare fixed-material and moving-contact-patch nonlinear IK responses."""
import math
def p3(a):
 if not isinstance(a,(tuple,list)) or len(a)!=3 or not all(type(x) in (int,float) and math.isfinite(x) for x in a):raise ValueError("NONFINITE_MATERIAL_POINT")
 return list(a)
def error(a,b):return round(math.dist(p3(a),p3(b)),6)
def classify(fixed_err,dynamic_err,threshold=.002):
 if any(type(x) not in (float,int) or not math.isfinite(x) or x<0 for x in (fixed_err,dynamic_err,threshold)):raise ValueError("ERROR_NONFINITE")
 if threshold<.0001 or threshold>.01:raise ValueError("ACCEPTANCE_THRESHOLD")
 return {"fixed_material_prediction_more_accurate":fixed_err+.000001<dynamic_err,
  "fixed_material_local_model_within_tolerance":fixed_err<=threshold,
  "moving_patch_model_within_tolerance":dynamic_err<=threshold,
  "source_plant_contact_admitted":False}
