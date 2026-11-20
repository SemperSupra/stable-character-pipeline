"""Independent fail-closed synthetic DoE analyser; no statistical claim from correlated frames."""
import argparse,json,math,sys
from pathlib import Path
EXPECTED_GEOMETRIES={"rigid","articulated_proxy","compliant_proxy"}
EXPECTED_CASES={"stance_early","stance_late","stance_noisy"}
EXPECTED_SOLVERS={"legacy","geometry_translation","geometry_rotation"}
KEYS=("max_penetration_m","max_stance_anchor_displacement_m","max_floating_m","mean_pose_deviation_m_equiv")
def analyse(p):
 if p.get("schema")!="scp.n03d.synthetic_screen.v1" or p.get("qualification")!="RESEARCH_ONLY_NOT_NATIVE_GAIT":raise ValueError("UNQUALIFIED_INPUT")
 rows=p.get("observations")
 if not isinstance(rows,list) or len(rows)!=27:raise ValueError("WRONG_FACTORIAL_CARDINALITY")
 seen=set()
 for r in rows:
  if not isinstance(r,dict) or set(r)!={"geometry","case","solver","metrics"}:raise ValueError("BAD_TREATMENT")
  k=(r["geometry"],r["case"],r["solver"])
  if k in seen or k[0] not in EXPECTED_GEOMETRIES or k[1] not in EXPECTED_CASES or k[2] not in EXPECTED_SOLVERS:raise ValueError("MISSING_OR_DUPLICATE_CELLS")
  seen.add(k)
  m=r["metrics"]
  if set(m)!=set(KEYS) or any(type(m[x]) not in (int,float) or not math.isfinite(m[x]) or m[x]<0 for x in KEYS):raise ValueError("INVALID_METRIC")
 if len(seen)!=27:raise ValueError("FACTORIAL_NOT_COMPLETE")
 results=[]
 for geometry in sorted(EXPECTED_GEOMETRIES):
  for case in sorted(EXPECTED_CASES):
   treatment=[r for r in rows if r["geometry"]==geometry and r["case"]==case]
   # A solution dominates only when no worse on each coordinate and strictly better on one.
   front=[]
   for a in treatment:
    am=a["metrics"]
    dominated=any(all(b["metrics"][k]<=am[k]+1e-12 for k in KEYS) and any(b["metrics"][k]<am[k]-1e-12 for k in KEYS) for b in treatment if b is not a)
    if not dominated:front.append(a["solver"])
   results.append({"geometry":geometry,"case":case,"nondominated_solvers":sorted(front)})
 return {"schema":"scp.n03d.synthetic_pareto.v1","status":"SCREENING_ONLY_NO_INFERENCE","blocks":results,"units":27,
         "n_native_mp_fitted":0,"anatomical_factor_is_proxy":True,"statistical_significance_claimed":False,
         "mvp_accepted":False}
def main():
 a=argparse.ArgumentParser();a.add_argument("input");a.add_argument("output");args=a.parse_args()
 data=analyse(json.loads(Path(args.input).read_text()))
 Path(args.output).write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
 print(json.dumps({"blocks":len(data["blocks"]),"status":data["status"]}))
if __name__=="__main__":main()
