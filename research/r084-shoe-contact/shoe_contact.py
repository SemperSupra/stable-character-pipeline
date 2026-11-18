"""R084 quantitative source-safe shoe contact and skate diagnostics.
No self-declared anatomical, gait or MVP acceptance from this metric.
"""
import math,statistics
SCHEMA="scp.r084.shoe-contact.v1"
GROUND_EPS_M=.012
SKATE_M_PER_SEC=.08
PENETRATION_M=.01
def require(ok,code):
 if not ok:raise ValueError(code)
def point(z,xy):
 require(type(z) in (float,int) and math.isfinite(z),"SOLE_Z_NONFINITE")
 require(len(xy)==2 and all(type(v) in (float,int) and math.isfinite(v) for v in xy),"SOLE_XY_NONFINITE")
 return {"z_m":float(z),"xy_m":[float(xy[0]),float(xy[1])]}
def quantify(samples,fps):
 require(type(fps) is int and 1<=fps<=240,"BAD_FRAME_CLOCK")
 require(type(samples) is list and len(samples)>=2,"TOO_FEW_SHOE_SAMPLES")
 entries=[]
 for s in samples:
  require(set(s)=={"z_m","xy_m"},"INVALID_SHOE_SAMPLE")
  entries.append(point(s["z_m"],s["xy_m"]))
 depth=max(0.,-min(x["z_m"] for x in entries))
 heel_height=max(x["z_m"] for x in entries)
 contacts=[i for i,v in enumerate(entries) if abs(v["z_m"])<=GROUND_EPS_M]
 slip=[]
 for i in range(1,len(entries)):
  p,q=entries[i-1],entries[i]
  if abs(p["z_m"])<=GROUND_EPS_M and abs(q["z_m"])<=GROUND_EPS_M:
   dx=math.hypot(q["xy_m"][0]-p["xy_m"][0],q["xy_m"][1]-p["xy_m"][1])
   slip.append(dx*fps)
 reasons=[]
 if depth>PENETRATION_M:reasons.append("PENETRATION_OVER_10MM")
 if not contacts:reasons.append("NO_GROUND_PROXIMITY")
 if slip and max(slip)>SKATE_M_PER_SEC:reasons.append("PLANTED_FOOT_SLIDING")
 if not slip:reasons.append("NO_TWO_CONSECUTIVE_CONTACT_SAMPLES")
 return {"status":"HOLD_CONTACT_"+("_".join(reasons) if reasons else "NEEDS_MOTION_REVIEW"),
         "samples":len(entries),"contact_frames":len(contacts),
         "minimum_z_m":round(min(x["z_m"] for x in entries),6),
         "maximum_z_m":round(heel_height,6),
         "penetration_m":round(depth,6),
         "maximum_contact_slip_m_per_s":round(max(slip),6) if slip else None,
         "flags":reasons,"gait_contact_accepted":False}
