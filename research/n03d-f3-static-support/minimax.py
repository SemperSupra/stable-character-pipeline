"""Deterministic exact planar minimum enclosing disk for short source support traces.
Not a kinematic IK solution nor physical contact admission.
"""
import math,itertools

def require_valid(points):
 if not isinstance(points,list) or not 2<=len(points)<=32:raise ValueError("WINDOW_BOUNDS")
 for p in points:
  if not isinstance(p,(list,tuple)) or len(p)!=2 or not all(type(z) in (int,float) and math.isfinite(z) and abs(z)<1e3 for z in p):
   raise ValueError("XY_NOT_FINITE")
def circum(a,b,c):
 ax,ay=a;bx,by=b;cx,cy=c
 d=2*(ax*(by-cy)+bx*(cy-ay)+cx*(ay-by))
 if abs(d)<1e-12:return None
 aa=ax*ax+ay*ay;bb=bx*bx+by*by;cc=cx*cx+cy*cy
 x=(aa*(by-cy)+bb*(cy-ay)+cc*(ay-by))/d
 y=(aa*(cx-bx)+bb*(ax-cx)+cc*(bx-ax))/d
 return (x,y)
def enclosing_disk(points):
 require_valid(points)
 # Exhaustive boundary <=3 for 2D Euclidean smallest enclosing ball,
 # deterministic and bounded to <=32 points, with no random seeds.
 p=[(float(x),float(y)) for x,y in points]
 def covers(c,r):
  return all(math.hypot(x-c[0],y-c[1])<=r+1e-8 for x,y in p)
 candidate=None
 def consider(c,r):
  nonlocal candidate
  if candidate is None or r<candidate["radius_m"]-1e-10:
   if covers(c,r):candidate={"center_xy_m":[c[0],c[1]],"radius_m":r}
 for x in p:consider(x,0.)
 for a,b in itertools.combinations(p,2):
  c=((a[0]+b[0])/2.,(a[1]+b[1])/2.)
  consider(c,math.dist(a,b)/2.)
 for a,b,c in itertools.combinations(p,3):
  center=circum(a,b,c)
  if center is not None:consider(center,math.dist(a,center))
 if candidate is None:raise ValueError("NO_NUMERIC_COVERING_DISK")
 return {"center_xy_m":[round(x,9) for x in candidate["center_xy_m"]],
  "minimax_radius_m":round(candidate["radius_m"],9),
  "boundary_model":"DETERMINISTIC_UP_TO_THREE_SOURCE_OBSERVATIONS",
  "stationary_support_proven":False}
