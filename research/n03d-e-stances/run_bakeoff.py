"""Held-out synthetic stance, slide, hover and source-quality classification."""
import json
from pathlib import Path
from segment import analyze
def fixture(kind):
 s=[]
 for i in range(96):
  plant=15<=i<37 or 56<=i<80
  h=.005 if plant else .095
  v=.012 if plant else .7
  if kind=="slide" and 56<=i<80:v=1.2
  if kind=="hover" and 15<=i<37:h=.055;v=.01
  if kind=="single" and i==45:h=.0;v=.0
  if kind=="ambiguity" and 27<=i<29:h=None;v=None
  s.append({"t_s":i/24,"z_m":h,"v_mps":v})
 return s
def main():
 cases={}
 for kind in ("clean","slide","hover","single","ambiguity"):
  cases[kind]=analyze(fixture(kind))
 print("N03D_E_SEGMENTER_BAKEOFF",json.dumps(cases,sort_keys=True))
 Path("n03d-evidence.json").write_text(json.dumps(cases,indent=2,sort_keys=True)+chr(10))
if __name__=="__main__":main()
