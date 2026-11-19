"""Velocities of identical shoe material vertices observed near ground on consecutive frames."""
import math,statistics
def compare_material_ids(previous,current,dt):
 if type(dt) not in (int,float) or not math.isfinite(dt) or not 0<dt<=1:raise ValueError("TIME_DELTA_INVALID")
 if not isinstance(previous,dict) or not isinstance(current,dict):raise ValueError("FRAME_DATA_TYPE_INVALID")
 common=set(previous)&set(current)
 if not common:return {"persistent_vertices":0,"median_mps":None,"p95_mps":None,"max_mps":None}
 speeds=[]
 for idx in common:
  a=previous[idx];b=current[idx]
  if len(a)!=2 or len(b)!=2 or not all(math.isfinite(x) for x in (*a,*b)):raise ValueError("NONFINITE_MATERIAL_VERTEX")
  speeds.append(math.hypot(a[0]-b[0],a[1]-b[1])/dt)
 speeds.sort()
 return {"persistent_vertices":len(speeds),"median_mps":round(statistics.median(speeds),6),
  "p95_mps":round(speeds[max(0,math.ceil(.95*len(speeds))-1)],6),
  "max_mps":round(speeds[-1],6)}
