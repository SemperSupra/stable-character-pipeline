"""Diagnostic only: compare real target bone near-minimum speed to source-pinned baseline."""
import math
def relative(new,old):
 if new is None or old is None:return None
 if not all(type(x) in (float,int) and math.isfinite(x) and x>=0 for x in (new,old)):raise ValueError("SPEED_NONFINITE")
 if old==0:return None
 return round(new/old,6)
def diagnostic(before,after):
 ratio=relative(after,before)
 return {"ratio":ratio,"speed_reduction_over_25pct":ratio is not None and ratio<.75,
  "physical_planted_contact_accepted":False}
