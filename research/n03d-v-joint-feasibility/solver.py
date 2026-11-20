"""Projected strongly-regularized temporal root/foot contact proxy solver.

All inputs are measured CC0 shoe support-patch centroids; the proxy is NOT a
persistently tracked sole material vertex nor an observed planted stance.
No corrected native animation is claimed by this numerical oracle.
"""
import math

SIDES=("rest_local_x_negative","rest_local_x_positive")
def vec(p):
 if not isinstance(p,(tuple,list)) or len(p)!=3 or any(type(v) not in (float,int) or not math.isfinite(v) or abs(v)>1e3 for v in p):
  raise ValueError("SOURCE_GEOMETRY_NONFINITE")
 return [float(v) for v in p]
def validate(points):
 if not isinstance(points,dict) or set(points)!=set(SIDES):raise ValueError("SOURCE_SIDES_INVALID")
 count=None
 for side in SIDES:
  q=points[side]
  if not isinstance(q,list) or not 4<=len(q)<=24:raise ValueError("WINDOW_COUNT_OUT_OF_BOUNDS")
  if count is not None and count!=len(q):raise ValueError("SIDE_TIMEBASE_MISMATCH")
  count=len(q)
  for p in q:vec(p)
 return count
def cap(x,bound):
 norm=math.sqrt(sum(z*z for z in x))
 if norm>bound:return [z*bound/norm for z in x]
 return list(x)
def state(n):
 return {"root":[[0.,0.,0.] for _ in range(n)],"foot":{s:[[0.,0.,0.] for _ in range(n)] for s in SIDES}}
def targets(points):
 return {s:[points[s][0][0],points[s][0][1],0.] for s in SIDES}
def objective(points,tar,st,lambda_r=.3,lambda_f=.3,lambda_t=1.):
 n=len(st["root"])
 energy=0.
 for t in range(n):
  for s in SIDES:
   e=[points[s][t][d]+st["root"][t][d]+st["foot"][s][t][d]-tar[s][d] for d in range(3)]
   energy+=sum(x*x for x in e)
  energy+=lambda_r*sum(x*x for x in st["root"][t])
  for s in SIDES:
   energy+=lambda_f*sum(x*x for x in st["foot"][s][t])
  if t:
   energy+=lambda_t*sum((st["root"][t][d]-st["root"][t-1][d])**2 for d in range(3))
   for s in SIDES:energy+=lambda_t*sum((st["foot"][s][t][d]-st["foot"][s][t-1][d])**2 for d in range(3))
 return energy
def gradient(points,tar,st,lambda_r=.3,lambda_f=.3,lambda_t=1.):
 n=len(st["root"])
 g=state(n)
 for t in range(n):
  for s in SIDES:
   for d in range(3):
    e=points[s][t][d]+st["root"][t][d]+st["foot"][s][t][d]-tar[s][d]
    g["root"][t][d]+=2*e
    g["foot"][s][t][d]+=2*e
  for d in range(3):g["root"][t][d]+=2*lambda_r*st["root"][t][d]
  for s in SIDES:
   for d in range(3):g["foot"][s][t][d]+=2*lambda_f*st["foot"][s][t][d]
  if t:
   for d in range(3):
    diff=st["root"][t][d]-st["root"][t-1][d]
    g["root"][t][d]+=2*lambda_t*diff;g["root"][t-1][d]-=2*lambda_t*diff
    for s in SIDES:
     diff=st["foot"][s][t][d]-st["foot"][s][t-1][d]
     g["foot"][s][t][d]+=2*lambda_t*diff;g["foot"][s][t-1][d]-=2*lambda_t*diff
 return g
def update(st,g,step,mode,bound):
 n=len(st["root"]);out=state(n)
 for t in range(n):
  if mode in ("root_only","joint"):
   out["root"][t]=cap([st["root"][t][d]-step*g["root"][t][d] for d in range(3)],bound)
  for s in SIDES:
   if mode in ("foot_only","joint"):
    out["foot"][s][t]=cap([st["foot"][s][t][d]-step*g["foot"][s][t][d] for d in range(3)],bound)
 return out
def solve(points,mode,bound=.04,iterations=320):
 n=validate(points)
 if mode not in ("root_only","foot_only","joint"):raise ValueError("UNKNOWN_OPTIMIZATION_MODE")
 if type(bound) not in (int,float) or not math.isfinite(bound) or not 0<bound<=.1:raise ValueError("ROOT_FOOT_BUDGET_INVALID")
 if not isinstance(iterations,int) or not 20<=iterations<=800:raise ValueError("COMPUTE_BUDGET_INVALID")
 tar=targets(points);st=state(n)
 before=objective(points,tar,st)
 hist=[before]
 for _ in range(iterations):
  g=gradient(points,tar,st)
  step=.05;current=hist[-1]
  for _ in range(16):
   nxt=update(st,g,step,mode,bound)
   value=objective(points,tar,nxt)
   if value<=current+1e-12:break
   step*=.5
  if value>current+1e-8:raise ValueError("OPTIMIZER_NONMONOTONE")
  st=nxt;hist.append(value)
 assert all(hist[i+1]<=hist[i]+1e-8 for i in range(len(hist)-1))
 residual=[]
 for t in range(n):
  for s in SIDES:
   p=[points[s][t][d]+st["root"][t][d]+st["foot"][s][t][d] for d in range(3)]
   residual.append({"side":s,"index":t,
     "xy_stationary_error_m":round(math.hypot(p[0]-tar[s][0],p[1]-tar[s][1]),6),
     "z_ground_error_m":round(p[2],6)})
 maxroot=max(math.dist(x,(0,0,0)) for x in st["root"])
 maxfoot=max(math.dist(x,(0,0,0)) for s in SIDES for x in st["foot"][s])
 return {"mode":mode,"samples_per_side":n,"bound_per_actor_component_m":bound,
   "objective_initial":round(before,8),"objective_final":round(hist[-1],8),
   "energy_nonincreasing":True,"solver_iterations":iterations,
   "max_root_correction_m":round(maxroot,6),"max_foot_correction_m":round(maxfoot,6),
   "max_xy_stationary_proxy_residual_m":max(x["xy_stationary_error_m"] for x in residual),
   "max_ground_proxy_penetration_m":max(0.,-min(x["z_ground_error_m"] for x in residual)),
   "max_ground_proxy_hover_m":max(0.,max(x["z_ground_error_m"] for x in residual)),
   "residual_by_side_frame":residual,
   "actual_native_after_correction_measured":False,
   "physical_contact_accepted":False,"mvp_accepted":False}
