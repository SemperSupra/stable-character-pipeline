"""Independent direct integer rational observer, does not import producer module."""
import json,sys
from pathlib import Path
MAX=(1<<63)-1
def observe():
 checks=0
 for n,d in ((12,1),(24,1),(30,1),(30000,1001)):
  for frame in range(1000):
   start=(frame*48000*d+n-1)//n
   video=(start*n)//(48000*d)
   previous=((start-1)*n)//(48000*d) if start>0 else -1
   if video!=frame or (frame>0 and previous>=frame):raise ValueError("INDEPENDENT_RATIONAL_BOUNDARY")
   checks+=1
 # Inverse false frame equality at 2^60 is not a valid source timestamp equality.
 high=1<<60
 if not float(high)==float(high+1) or (high+1)-high!=1:raise ValueError("FLOAT_COLLAPSE_NEGATIVE_CONTROL")
 for s,expect in ((4000,1),(16000,4)):
  if (s*12)//48000!=expect:raise ValueError("W16_FOLEY_EVENT_MAPPING")
 r={"schema":"scp.w4j_b2_independent_rational_oracle.v1","status":"PASS_SOURCE_INTEGER_RATIONAL_48K","boundary_cases":checks,"high_tick_source_delta":1,"float_collapse_detected":True,"w16_source_contact_samples":[4000,16000],"scope":"NO_ABSOLUTE_RENDERER_LATENCY_NO_UNTIMED_RIG_CLOCK_CLAIM"}
 Path(sys.argv[1]).write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
 print("W4J_B2_RATIONAL_INDEPENDENT_PASS",checks)
if __name__=="__main__":observe()
