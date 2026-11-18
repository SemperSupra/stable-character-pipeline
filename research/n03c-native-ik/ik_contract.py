"""Source-safe original contract for known MPFB 5-bone IK chain and witness."""
import math
def chain(side):
 if side not in ("L","R"):raise ValueError("UNSUPPORTED_SIDE")
 return tuple(x+"."+side for x in ("foot","lowerleg02","lowerleg01","upperleg02","upperleg01"))
def validate_parents(side,parents):
 expected=chain(side)
 if not isinstance(parents,dict):raise ValueError("INVALID_PARENTS")
 for a,b in zip(expected,expected[1:]):
  if parents.get(a)!=b:raise ValueError("UNQUALIFIED_NATIVE_CHAIN")
 if parents.get(expected[-1])!="pelvis."+side:raise ValueError("UNQUALIFIED_NATIVE_PELVIS")
 return expected
def classify(rows):
 if not isinstance(rows,list) or len(rows)<3:raise ValueError("INSUFFICIENT_POSE_SAMPLES")
 moving=0;improved=0;danger=False
 for row in rows:
  if not isinstance(row,dict) or set(row)!={"before_target_error_m","after_target_error_m","root_pose_drift_m","shoe_min_z_m"}:raise ValueError("INVALID_SAMPLE_SCHEMA")
  if any(type(x) not in (int,float) or not math.isfinite(x) for x in row.values()):raise ValueError("NONFINITE_POSE")
  if any(row[k]<0 for k in ("before_target_error_m","after_target_error_m","root_pose_drift_m")):raise ValueError("INVALID_DISTANCE")
  if row["root_pose_drift_m"]>.0005:raise ValueError("ROOT_MUTATION")
  if row["before_target_error_m"]>.001:
   moving+=1
   if row["after_target_error_m"]+1e-6<row["before_target_error_m"]:improved+=1
  if row["shoe_min_z_m"]<-.01:danger=True
 return {"moving_samples":moving,"improved_samples":improved,
         "native_ik_effect_observed":improved>0,
         "shoe_floor_penetration_hazard":danger,"physical_contact_accepted":False,
         "mvp_accepted":False}
