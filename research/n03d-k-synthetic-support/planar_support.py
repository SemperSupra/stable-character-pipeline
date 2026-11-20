"""Original synthetic planar five-bone leg and exact heel/toe support Jacobian.
This is a *numerical* reference only, not a calibrated MPFB anatomy or native Blender rig.
"""
import math
LINKS=(.42,.20,.17,.12,.08)
HEEL=(-.12,-.06)
TOE=(.12,-.06)
def finite_angles(theta):
 if not isinstance(theta,(tuple,list)) or len(theta)!=5:
  raise ValueError("FIVE_ANGLE_LAYOUT")
 if any(type(a) not in (int,float) or not math.isfinite(a) or abs(a)>1.2 for a in theta):
  raise ValueError("UNSUPPORTED_JOINT_OR_NONFINITE")
 return tuple(float(a) for a in theta)
def fk(theta,pelvis):
 a=finite_angles(theta)
 if not isinstance(pelvis,(tuple,list)) or len(pelvis)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) for x in pelvis):
  raise ValueError("PELVIS_LAYOUT")
 phi=[];cum=0.
 for th in a:
  cum+=th;phi.append(cum)
 x=float(pelvis[0])+sum(L*math.sin(p) for L,p in zip(LINKS,phi))
 z=float(pelvis[1])-sum(L*math.cos(p) for L,p in zip(LINKS,phi))
 return x,z,cum,phi
def positions(theta,pelvis):
 x,z,angle,_=fk(theta,pelvis)
 result=[]
 for u,v in (HEEL,TOE):
  result.extend((x+u*math.cos(angle)-v*math.sin(angle),
                 z+u*math.sin(angle)+v*math.cos(angle)))
 return tuple(result)
def jacobian(theta,pelvis):
 x,z,angle,phi=fk(theta,pelvis)
 out=[[0.]*5 for _ in range(4)]
 for k in range(5):
  dx=sum(L*math.cos(phi[j]) for j,L in enumerate(LINKS) if j>=k)
  dz=sum(L*math.sin(phi[j]) for j,L in enumerate(LINKS) if j>=k)
  for n,(u,v) in enumerate((HEEL,TOE)):
   out[2*n][k]=dx-u*math.sin(angle)-v*math.cos(angle)
   out[2*n+1][k]=dz+u*math.cos(angle)-v*math.sin(angle)
 return out
def support_error(theta,pelvis,target):
 return max(math.hypot(a-b,c-d) for (a,c),(b,d) in zip(zip(positions(theta,pelvis)[::2],positions(theta,pelvis)[1::2]),zip(target[::2],target[1::2])))
