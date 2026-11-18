"""Original synthetic square-surface exact oracle; dependency-free."""
import math
import random

def require(ok,code):
 if not ok:raise ValueError(code)

def check_point(q):
 require(isinstance(q,(tuple,list)) and len(q)==3,"BAD_POINT_LAYOUT")
 require(all(type(x) in (int,float) and math.isfinite(x) for x in q),"BAD_POINT_COORDINATE")
 return tuple(float(x) for x in q)

def exact_square(q):
 """Nearest point to the closed, coplanar square [-1,1]^2, z=0."""
 x,y,z=check_point(q)
 return (max(-1.,min(1.,x)),max(-1.,min(1.,y)),0.)

def exact_distance(q):
 x,y,z=check_point(q)
 a,b,c=exact_square(q)
 return math.sqrt((x-a)**2+(y-b)**2+(z-c)**2)

def grid(subdivisions):
 require(type(subdivisions) is int and 2<=subdivisions<=128,"INVALID_RESOLUTION")
 n=subdivisions
 vertices=[(-1+2*i/n,-1+2*j/n,0.) for j in range(n+1) for i in range(n+1)]
 triangles=[]
 for j in range(n):
  for i in range(n):
   a=j*(n+1)+i
   b=a+1;c=a+(n+1);d=c+1
   triangles.extend(((a,b,c),(b,d,c)))
 return vertices,triangles

def queries(count=4096,seed=20261118):
 require(type(count) is int and 64<=count<=10000,"INVALID_QUERY_COUNT")
 rng=random.Random(seed)
 out=[(rng.uniform(-1.25,1.25),rng.uniform(-1.25,1.25),rng.uniform(-.40,.40)) for _ in range(count)]
 out.extend([(0.,0.,0.),(.005,.005,.025),(-1.,1.,.0),(1.1,1.2,-.05),(-1.3,-1.2,.1)])
 return out
