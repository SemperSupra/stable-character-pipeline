"""Source-root planar similarity alignment: least-squares yaw, scale, translation."""
import math
def check(seq):
 if not isinstance(seq,list) or not 5<=len(seq)<=1000:raise ValueError("SAMPLE_BOUNDS")
 if any(len(p)!=2 or not all(type(x) in (float,int) and math.isfinite(x) for x in p) for p in seq):raise ValueError("NONFINITE_POINTS")
 return [(float(x),float(y)) for x,y in seq]
def fit(source,target):
 a,b=check(source),check(target)
 if len(a)!=len(b):raise ValueError("CLOCK_DRIFT")
 mx=sum(x for x,y in a)/len(a);my=sum(y for x,y in a)/len(a)
 nx=sum(x for x,y in b)/len(b);ny=sum(y for x,y in b)/len(b)
 var=sum((x-mx)**2+(y-my)**2 for x,y in a)
 if var<1e-9:raise ValueError("DEGENERATE_SOURCE_PATH")
 c=sum((x-mx)*(u-nx)+(y-my)*(v-ny) for (x,y),(u,v) in zip(a,b))
 s=sum((x-mx)*(v-ny)-(y-my)*(u-nx) for (x,y),(u,v) in zip(a,b))
 length=math.hypot(c,s)
 if length<1e-9:raise ValueError("YAW_UNIDENTIFIABLE")
 scale=length/var
 if not .01<=scale<=100:raise ValueError("SCALE_OUT_OF_RANGE")
 c/=length;s/=length
 return {"scale":scale,"cos":c,"sin":s,"dx":nx-scale*(c*mx-s*my),"dy":ny-scale*(s*mx+c*my)}
def transform(model,source):
 a=check(source)
 scale,c,s,dx,dy=(model[k] for k in ("scale","cos","sin","dx","dy"))
 if not math.isfinite(scale) or scale<=0 or abs(c*c+s*s-1)>1e-5:raise ValueError("BAD_TRANSFORM")
 return [(scale*(c*x-s*y)+dx,scale*(s*x+c*y)+dy) for x,y in a]
def error(pred,target):
 a,b=check(pred),check(target)
 if len(a)!=len(b):raise ValueError("HELDOUT_CLOCK_DRIFT")
 d=[math.dist(x,y) for x,y in zip(a,b)]
 return round(math.sqrt(sum(x*x for x in d)/len(d)),6)
