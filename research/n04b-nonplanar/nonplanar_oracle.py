"""Independent Ericson triangle closest point and synthetic nonplanar deformations.
All inputs are constructed original public-safe grids; no identity or sourced assets.
"""
import math,random
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'n04-surface'))
from geometry_contract import grid,check_point
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def add(a,b,k):return tuple(x+k*y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def distance2(a,b):return dot(sub(a,b),sub(a,b))
def closest_triangle(p,a,b,c):
 p,a,b,c=map(check_point,(p,a,b,c))
 ab,ac,ap=sub(b,a),sub(c,a),sub(p,a)
 # Reject degenerate input, otherwise Ericson Voronoi-region projection.
 area2=dot(ab,ab)*dot(ac,ac)-dot(ab,ac)**2
 if area2<=1e-20:raise ValueError("DEGENERATE_TRIANGLE")
 d1,d2=dot(ab,ap),dot(ac,ap)
 if d1<=0 and d2<=0:return a
 bp=sub(p,b);d3,d4=dot(ab,bp),dot(ac,bp)
 if d3>=0 and d4<=d3:return b
 vc=d1*d4-d3*d2
 if vc<=0 and d1>=0 and d3<=0:return add(a,ab,d1/(d1-d3))
 cp=sub(p,c);d5,d6=dot(ab,cp),dot(ac,cp)
 if d6>=0 and d5<=d6:return c
 vb=d5*d2-d1*d6
 if vb<=0 and d2>=0 and d6<=0:return add(a,ac,d2/(d2-d6))
 va=d3*d6-d5*d4
 if va<=0 and (d4-d3)>=0 and (d5-d6)>=0:
  bc=sub(c,b);w=(d4-d3)/((d4-d3)+(d5-d6))
  return add(b,bc,w)
 denom=va+vb+vc
 if abs(denom)<1e-20:raise ValueError("DEGENERATE_BARYCENTRIC")
 v=vb/denom;w=vc/denom
 return tuple(a[i]+ab[i]*v+ac[i]*w for i in range(3))

def wavy_mesh(phase,n=8):
 if not isinstance(phase,(float,int)) or isinstance(phase,bool) or not math.isfinite(phase):raise ValueError("BAD_PHASE")
 verts,faces=grid(n)
 # Continuous, nonlinear, nonplanar deformation; fixed topology and vertex IDs.
 transformed=[(x,y,.17*math.sin(math.pi*(x+.1))*math.cos(math.pi*(y-.15))*math.sin(phase+.5*x)) for x,y,_ in verts]
 return transformed,faces
def queries(phase,count=96):
 rng=random.Random(12345+int(1000*phase))
 pts=[]
 for _ in range(count):
  x=rng.uniform(-1.15,1.15);y=rng.uniform(-1.15,1.15)
  z=.17*math.sin(math.pi*(x+.1))*math.cos(math.pi*(y-.15))*math.sin(phase+.5*x)+rng.uniform(-.15,.15)
  pts.append((x,y,z))
 pts +=[(0.,0.,0.),(1.3,1.4,.1),(-1.,-1.,-.1)]
 return pts
def reference_distances(verts,faces,pts):
 for v in verts:check_point(v)
 if not faces or any(len(t)!=3 or min(t)<0 or max(t)>=len(verts) or len(set(t))!=3 for t in faces):raise ValueError("BAD_TOPOLOGY")
 return [math.sqrt(min(distance2(p,closest_triangle(p,*(verts[i] for i in face))) for face in faces)) for p in pts]
