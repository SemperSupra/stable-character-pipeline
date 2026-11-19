"""Run adversarial independent contact admission, intentionally preserve physical RED."""
import json
from pathlib import Path
from gate import decide
from test_gate import fixture
cases={}
for name in ("clean","hover","skate","penetration"):
 cases[name]=decide(fixture(name))
 if name!="clean" and cases[name]["contact_metrics_pass_narrow"]:
  raise AssertionError("GATE_FALSE_PASS_"+name)
 if name=="clean" and not cases[name]["contact_metrics_pass_narrow"]:
  raise AssertionError("GATE_FALSE_NEGATIVE_CLEAN")
Path("n03d-g-evidence.json").write_text(json.dumps(cases,sort_keys=True,indent=2)+chr(10))
print("N03D_G_INDEPENDENT_CONTACT_CRITIC",json.dumps({k:{"status":v["status"],"mvp_accepted":v["mvp_accepted"]} for k,v in cases.items()},sort_keys=True),flush=True)
