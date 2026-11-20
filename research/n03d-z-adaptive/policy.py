"""Fail-closed actual/native shoe-probe trust screening, never accept gait."""
import math
def norm(x):
 if not isinstance(x,(tuple,list)) or len(x)!=3 or not all(type(z) in (int,float) and math.isfinite(z) for z in x):raise ValueError("NONFINITE_PROBE")
 return math.sqrt(sum(float(z)**2 for z in x))
def screen(before,after,prediction,delta,jacobian_norm,trust,model_tol=.002):
 b=norm(before);a=norm(after);p=norm(prediction);step=norm(delta)
 if not all(type(x) in (int,float) and math.isfinite(x) for x in (jacobian_norm,trust,model_tol)):raise ValueError("NONFINITE_POLICY")
 if not 0<trust<=.01 or not .0001<=model_tol<=.01:raise ValueError("TRUST_POLICY_BOUNDS")
 if step>trust+1e-7:raise ValueError("TRUST_EXCEEDED")
 gap=math.dist(after,prediction)
 gain=b-a
 # High local slope, changing-support patch or non-predictive step invalidate.
 admissible=(jacobian_norm<=10. and gap<=model_tol and gain>.0001)
 reason=("OK_NUMERIC_ONLY" if admissible else
  "JACOBIAN_SENSITIVE" if jacobian_norm>10 else
  "MODEL_MISMATCH" if gap>model_tol else "NO_REAL_RESIDUAL_IMPROVEMENT")
 return {"numeric_candidate_admissible":bool(admissible),"reason":reason,
  "native_residual_before_m":round(b,6),"native_residual_after_m":round(a,6),
  "prediction_gap_m":round(gap,6),"actual_residual_improvement_m":round(gain,6),
  "native_physical_contact_accepted":False}
def select(rows):
 if not isinstance(rows,list) or not rows:raise ValueError("NO_NATIVE_CANDIDATES")
 allowed=[r for r in rows if r["assessment"]["numeric_candidate_admissible"]]
 best=min(allowed,key=lambda r:(r["assessment"]["native_residual_after_m"],r["trust_radius_m"])) if allowed else None
 return {"chosen_trust_radius_m":None if best is None else best["trust_radius_m"],
  "no_numerical_candidate":best is None,
  "source_heldout_contact_tested":False,"physical_footplant_accepted":False}
