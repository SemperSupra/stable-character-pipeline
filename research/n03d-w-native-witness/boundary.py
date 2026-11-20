"""Solver numerical result to native actuation admission boundary."""
import math
def validate(result):
 if result.get("mode") not in ("root_only","foot_only","joint"):raise ValueError("UNKNOWN_SOLVER_MODE")
 n=result.get("samples_per_side");root=result.get("root_corrections_m");foot=result.get("foot_corrections_m")
 if type(n)!=int or n<4 or not isinstance(root,list) or len(root)!=n:raise ValueError("MISSING_ROOT_CORRECTIONS")
 if not isinstance(foot,dict) or set(foot)!={"rest_local_x_negative","rest_local_x_positive"}:raise ValueError("FOOT_SIDE_SET")
 for seq in [root,*foot.values()]:
  if len(seq)!=n:raise ValueError("SAMPLE_CLOCK_DISAGREEMENT")
  for xyz in seq:
   if not isinstance(xyz,list) or len(xyz)!=3 or not all(type(x) in (float,int) and math.isfinite(x) for x in xyz):raise ValueError("NONFINITE_ACTUATOR")
   if math.sqrt(sum(x*x for x in xyz))>.040001:raise ValueError("MOVEMENT_BUDGET")
 if result.get("physical_contact_accepted") is not False or result.get("actual_native_after_correction_measured") is not False:raise ValueError("UNAUTHORIZED_NATIVE_PASS")
 return True
