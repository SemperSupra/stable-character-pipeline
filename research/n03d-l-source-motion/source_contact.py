"""R098L 100STYLE exact source 60Hz ankle/toe near-ground evidence, no skin/sole contact claim."""
import math,statistics
def summarize(points,dt,height_tolerance=.02,slow_threshold=.08,minimum_consecutive=3):
 if type(dt) not in (int,float) or not math.isfinite(dt) or dt<=0 or dt>.05:raise ValueError("CLOCK_OUT_OF_RANGE")
 if not isinstance(points,list) or len(points)<20 or len(points)>25000:raise ValueError("SAMPLE_BOUNDS")
 if not all(isinstance(p,(tuple,list)) and len(p)==3 and all(type(x) in (float,int) and math.isfinite(x) and abs(x)<10000 for x in p) for p in points):raise ValueError("SOURCE_POS_NONFINITE")
 floor=min(p[1] for p in points)
 proximity=[p[1]-floor<=height_tolerance for p in points]
 speeds=[]
 near_pairs=[]
 slow=[]
 for i in range(1,len(points)):
  a,b=points[i-1],points[i]
  v=math.hypot(a[0]-b[0],a[2]-b[2])/dt
  speeds.append(v)
  if proximity[i-1] and proximity[i]:
   near_pairs.append(v)
   slow.append(v<=slow_threshold)
  else:slow.append(False)
 episodes=[];start=None
 for i,x in enumerate(slow):
  if x and start is None:start=i
  if (not x or i==len(slow)-1) and start is not None:
   stop=i if x else i-1
   if stop-start+1>=minimum_consecutive:
    episodes.append({"start_interval":start,"last_interval":stop,"consecutive_pairs":stop-start+1,"duration_s":round((stop-start+1)*dt,6)})
   start=None
 def percentile(v,q):
  if not v:return None
  a=sorted(v)
  return round(a[min(len(a)-1,math.ceil(q*len(a))-1)],6)
 return {"sample_count":len(points),"min_observed_height_m":round(floor,6),
  "near_minimum_samples":sum(proximity),"near_minimum_adjacent_pairs":len(near_pairs),
  "near_ground_p50_world_speed_mps":round(statistics.median(near_pairs),6) if near_pairs else None,
  "near_ground_p95_world_speed_mps":percentile(near_pairs,.95),
  "overall_p50_speed_mps":round(statistics.median(speeds),6),
  "slow_near_ground_episodes":episodes,
  "slow_episode_count":len(episodes),
  "source_true_ground_contact_proven":False}
