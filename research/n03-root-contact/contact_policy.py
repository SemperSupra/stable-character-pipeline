"""N03 root-only contact feasibility: original synthetic, no rig or source modifications."""
import math
EPS=0.012
MAX_ROOT_Z_M=0.12
MAX_ROOT_XY_M=0.12

def require(cond,code):
 if not cond:raise ValueError(code)

def point(z,xy):
 require(type(z) in (int,float) and math.isfinite(z),"BAD_Z")
 require(isinstance(xy,(tuple,list)) and len(xy)==2 and all(type(v) in (int,float) and math.isfinite(v) for v in xy),"BAD_XY")
 return {"z_m":float(z),"xy_m":(float(xy[0]),float(xy[1]))}

def plan(baseline):
 """A per-frame root translation minimizing squared planar contact anchor drift.
 This is ONLY an algebraic root-level proposal, not rig/contact optimization.
 """
 require(isinstance(baseline,list) and len(baseline)>=3,"BAD_TRAJECTORY")
 sides=("x_negative","x_positive")
 anchors={}
 rows=[]
 peak_conflict=0.0
 for i,parts in enumerate(baseline):
  require(isinstance(parts,dict) and set(parts)==set(sides),"BAD_SHOE_PARTITIONS")
  v={side:point(parts[side]["z_m"],parts[side]["xy_m"]) for side in sides}
  minimum=min(v[s]["z_m"] for s in sides)
  dz=max(0.0,-minimum)
  require(dz<=MAX_ROOT_Z_M,"NECESSARY_LIFT_EXCEEDS_ROOT_ONLY_LIMIT")
  active=[s for s in sides if v[s]["z_m"]+dz<=EPS]
  for s in sides:
   if s not in active:anchors.pop(s,None)
   elif s not in anchors:anchors[s]=v[s]["xy_m"]
  proposals=[(anchors[s][0]-v[s]["xy_m"][0],anchors[s][1]-v[s]["xy_m"][1]) for s in active]
  if proposals:
   dx=sum(p[0] for p in proposals)/len(proposals)
   dy=sum(p[1] for p in proposals)/len(proposals)
   if len(proposals)==2:
    conflict=math.hypot(proposals[0][0]-proposals[1][0],proposals[0][1]-proposals[1][1])/2
    peak_conflict=max(peak_conflict,conflict)
  else:dx=dy=0.
  norm=math.hypot(dx,dy)
  if norm>MAX_ROOT_XY_M:
   dx*=MAX_ROOT_XY_M/norm
   dy*=MAX_ROOT_XY_M/norm
  rows.append({"frame":i,"root_offset_m":(dx,dy,dz),"support_partitions":active,
               "unconstrained_xy_correction_m":norm})
 return {"frames":rows,"max_simultaneous_contact_conflict_lower_bound_m":peak_conflict,
         "root_only_candidate":True,"gait_accepted":False}

def root_velocity(rows,fps):
 require(type(fps) is int and 1<=fps<=240,"INVALID_FPS")
 offsets=[r["root_offset_m"] for r in rows]
 return max(math.dist(a,b)*fps for a,b in zip(offsets,offsets[1:]))
