"""N03D F2 source-safe contact-target bounded correction and independent numeric gates.
No physical gait or biological contact certification.
"""
import math
def bounded_sole_z(z_m,target_gap_m=.002,limit_m=.04):
 if not all(type(x) in (float,int) and math.isfinite(x) for x in (z_m,target_gap_m,limit_m)):
  raise ValueError("SOURCE_CONTACT_NONFINITE")
 if not 0<=target_gap_m<=.01 or not 0<limit_m<=.05:raise ValueError("BAD_TARGET_BUDGET")
 return min(limit_m,max(0.,target_gap_m-z_m))
def outcome(before,after,root_drift,correction):
 if len(before)!=len(after) or len(before)<5:raise ValueError("INSUFFICIENT_ACTUAL_SAMPLES")
 if not all(type(x) in (int,float) and math.isfinite(x) for x in (*before,*after,root_drift,correction)):
  raise ValueError("SAMPLE_NONFINITE")
 if root_drift>.001 or correction>.05:raise ValueError("ROOT_OR_CONTACT_BUDGET_EXCEEDED")
 b=min(before);a=min(after)
 return {"before_max_penetration_m":round(max(0.,-b),6),
   "after_max_penetration_m":round(max(0.,-a),6),
   "before_min_sole_z_m":round(b,6),"after_min_sole_z_m":round(a,6),
   "penetration_improvement_m":round(max(0.,-b)-max(0.,-a),6),
   "after_penetration_below_10mm":a>=-.01,
   "after_lowest_shoe_in_ground_band":-.01<=a<=.01,
   "after_all_sampled_frames_hover_above_10mm":all(z>.01 for z in after),
   "near_ground_sample_count":sum(1 for z in after if -.012<=z<=.012),
   "post_ik_natural_gait_accepted":False}
