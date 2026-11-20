"""Finite-difference shoe-point IK Jacobian, damped least-squares and trust-region bounds."""
import math
def check3(values):
 if not isinstance(values,(tuple,list)) or len(values)!=3 or not all(type(x) in (int,float) and math.isfinite(x) for x in values):
  raise ValueError("NONFINITE_3D")
 return [float(x) for x in values]
def jacobian(plus,minus,step):
 if not isinstance(plus,list) or not isinstance(minus,list) or len(plus)!=3 or len(minus)!=3:raise ValueError("NOT_THREE_AXES")
 if type(step) not in (int,float) or not 1e-5<=step<=.005:raise ValueError("FD_STEP_BOUNDS")
 cols=[]
 for p,m in zip(plus,minus):
  a,b=check3(p),check3(m)
  cols.append([(a[i]-b[i])/(2*step) for i in range(3)])
 return [[cols[k][d] for k in range(3)] for d in range(3)]
def solve3(matrix,vec):
 a=[row[:]+[x] for row,x in zip(matrix,vec)]
 for k in range(3):
  pivot=max(range(k,3),key=lambda i:abs(a[i][k]))
  if abs(a[pivot][k])<1e-12:raise ValueError("SINGULAR_DAMPED_SYSTEM")
  a[k],a[pivot]=a[pivot],a[k]
  f=a[k][k]
  for j in range(k,4):a[k][j]/=f
  for i in range(3):
   if i==k:continue
   f=a[i][k]
   for j in range(k,4):a[i][j]-=f*a[k][j]
 return [a[i][3] for i in range(3)]
def update(j,residual,damping=.1,trust=.01):
 if not isinstance(j,list) or len(j)!=3 or not all(isinstance(row,list) and len(row)==3 for row in j):raise ValueError("JACOBIAN_SHAPE")
 for row in j:check3(row)
 r=check3(residual)
 if not 0<damping<=10 or not 0<trust<=.02:raise ValueError("REGULARIZATION_BOUNDS")
 gram=[[sum(j[k][i]*j[k][q] for k in range(3))+(damping if i==q else 0) for q in range(3)] for i in range(3)]
 right=[-sum(j[k][i]*r[k] for k in range(3)) for i in range(3)]
 delta=solve3(gram,right)
 norm=math.sqrt(sum(v*v for v in delta))
 if norm>trust:delta=[v*trust/norm for v in delta]
 predicted=[r[i]+sum(j[i][k]*delta[k] for k in range(3)) for i in range(3)]
 magnitude=math.sqrt(sum(v*v for row in j for v in row))
 return {"target_delta_m":delta,"predicted_residual_m":predicted,
  "jacobian_frobenius_norm":round(magnitude,6),
  "jacobian_near_zero_rank_warning":magnitude<.05,
  "trust_bound_m":trust,"motion_physically_valid":False}
