"""Separate stdlib pass/fail critique of actual Blender JSON, no implicit waiver."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent.parent/"n03d-g-contact-critic"))
from gate import decide
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--source",required=True);p.add_argument("--out",required=True)
 args=p.parse_args()
 source=json.loads(Path(args.source).read_text())
 verdict=decide(source)
 if verdict["mvp_accepted"] or verdict["release_authorized"] or verdict["human_naturalness_proven"]:
  raise ValueError("FORBIDDEN_GATE_PROMOTION")
 Path(args.out).write_text(json.dumps(verdict,sort_keys=True,indent=2,allow_nan=False)+chr(10))
 print("N03D_D_INDEPENDENT_ACTUAL_24HZ_VERDICT",json.dumps({"status":verdict["status"],
   "reasons":verdict["fail_reasons"],"actors":verdict["actors"],"mvp":False},sort_keys=True),flush=True)
if __name__=="__main__":main()
