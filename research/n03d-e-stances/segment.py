"""N03D-E recorded-source-ready contact segmentation, synthetic qualification only.
No sensor-inferred stance is ground truth contact or legal asset admission.
"""
import math

UNKNOWN="UNKNOWN"
STANCE="STANCE_CANDIDATE"
SWING="SWING"
STATES=(STANCE,SWING)
SAMPLE_LIMIT=50000

def validate(samples):
 if not isinstance(samples,list) or not 2<=len(samples)<=SAMPLE_LIMIT:
  raise ValueError("SAMPLE_WINDOW_BOUNDS")
 times=[]
 for sample in samples:
  if not isinstance(sample,dict) or not {"t_s","z_m","v_mps"}<=sample.keys():
   raise ValueError("SAMPLE_SCHEMA")
  t=sample["t_s"];z=sample["z_m"];v=sample["v_mps"]
  if type(t) not in (float,int) or not math.isfinite(t):
   raise ValueError("CLOCK_NONFINITE")
  if times and (t-times[-1])<=0 or (t-times[-1])>1.:
   raise ValueError("CLOCK_NONMONOTONIC_OR_GAP")
  times.append(t)
  if z is None or v is None:continue
  if type(z) not in (float,int) or type(v) not in (float,int) or not all(math.isfinite(x) for x in (z,v)) or v<0 or abs(z)>3 or v>50:
   raise ValueError("MEASUREMENT_NONFINITE_OR_OUT_OF_RANGE")
 return True

def _plausible(x, z_enter=.018, v_enter=.09):
 return x["z_m"] is not None and x["v_mps"] is not None and -0.20<x["z_m"]<=z_enter and x["v_mps"]<=v_enter

def threshold(samples):
 validate(samples)
 return [STANCE if _plausible(x) else (UNKNOWN if x["z_m"] is None or x["v_mps"] is None else SWING) for x in samples]

def hysteresis(samples, dwell=3):
 validate(samples)
 if dwell<2:raise ValueError("MIN_DWELL_REQUIRED")
 n=len(samples);labels=[UNKNOWN]*n
 state=UNKNOWN;since=0
 for i,x in enumerate(samples):
  if x["z_m"] is None or x["v_mps"] is None:
   state=UNKNOWN;since=i+1
   continue
  enter=_plausible(x,.019,.10)
  leave=x["z_m"]>.035 or x["v_mps"]>.19
  if state==STANCE:
   if leave:
    state=UNKNOWN;since=i;labels[i]=UNKNOWN
   else:labels[i]=STANCE
  elif state==SWING:
   if enter:
    state=UNKNOWN;since=i;labels[i]=UNKNOWN
   else:labels[i]=SWING
  if state==UNKNOWN:
   want=STANCE if enter else (SWING if leave else UNKNOWN)
   if want==UNKNOWN:
    since=i+1
   elif i>since and all(((_plausible(s,.019,.10)) if want==STANCE else (s["z_m"] is not None and s["v_mps"] is not None and (s["z_m"]>.035 or s["v_mps"]>.19))) for s in samples[since:i+1]):
    if i-since+1>=dwell:
     for k in range(since,i+1):labels[k]=want
     state=want
   else:since=i
 return labels

def viterbi(samples, switch_penalty=4.):
 validate(samples)
 def emission(x,state):
  z=x["z_m"];v=x["v_mps"]
  if z is None or v is None:return 2.
  if state==STANCE:
   return (max(0.,z-.018)/.025)**2+(max(0.,v-.09)/.10)**2+(max(0.,-.01-z)/.015)**2
  return (max(0.,.05-z)/.035)**2+(max(0.,.18-v)/.22)**2
 n=len(samples);d=[{state:emission(samples[0],state) for state in STATES}];back=[]
 for i in range(1,n):
  bp={};cur={}
  for st in STATES:
   best=min(STATES,key=lambda previous:d[-1][previous]+(switch_penalty if previous!=st else 0))
   bp[st]=best
   cur[st]=d[-1][best]+(switch_penalty if best!=st else 0)+emission(samples[i],st)
  back.append(bp);d.append(cur)
 st=min(STATES,key=lambda s:d[-1][s]);seq=[st]
 for bp in reversed(back):
  st=bp[st];seq.append(st)
 seq.reverse()
 # Missing data and isolated/short candidate episodes are NOT planted-foot proof.
 for i,x in enumerate(samples):
  if x["z_m"] is None or x["v_mps"] is None:seq[i]=UNKNOWN
 return seq

def qualified_segments(labels, samples, minimum=3):
 if len(labels)!=len(samples) or minimum<2:raise ValueError("BAD_SEGMENT_INPUT")
 segments=[];i=0
 while i<len(labels):
  if labels[i]!=STANCE:
   i+=1;continue
  start=i
  while i<len(labels) and labels[i]==STANCE:i+=1
  length=i-start
  if length>=minimum:
   segments.append({"first_index":start,"last_index":i-1,"samples":length,
     "t_start_s":samples[start]["t_s"],"t_end_s":samples[i-1]["t_s"]})
 return segments

def analyze(samples):
 validate(samples)
 output={}
 for name,fn in (("height_velocity",threshold),("hysteresis_min_dwell",hysteresis),("viterbi_transition_cost",viterbi)):
  labels=fn(samples)
  segments=qualified_segments(labels,samples)
  output[name]={"raw_candidate_frames":labels.count(STANCE),"segments":segments,
   "segmented_contact_evidence":bool(segments),
   "physical_foot_plant_accepted":False}
 sliding=[i for i,x in enumerate(samples) if x["z_m"] is not None and x["v_mps"] is not None and -0.012<=x["z_m"]<=.012 and x["v_mps"]>.08]
 penetration=[i for i,x in enumerate(samples) if x["z_m"] is not None and x["z_m"]<-.01]
 return {"schema":"scp.n03d-e.contact-segment-comparison.v1","algorithms":output,
  "near_ground_skate_sample_indices":sliding,"penetration_over_10mm_sample_indices":penetration,
  "evidence_level":"SYNTHETIC_FIXTURE_ONLY", "actual_natural_gait_accepted":False,
  "release_authorized":False}
