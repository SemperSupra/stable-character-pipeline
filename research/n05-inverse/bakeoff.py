"""N05 synthetic constrained inverse, analytic Jacobian vs FD and linear SVD baseline."""
import hashlib,importlib.metadata,json,math,platform,sys,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from morphology_contract import LATENTS,MEASURES,BIAS,A,predict,jacobian,validate_measurements,assess_observability
def array_model(x):
 return np.array(validate_measurements(predict([float(t) for t in x])))
def fit(y,mode):
 seed=np.zeros(4)
 def fun(x):return (array_model(x)-y)/.01
 jac=(lambda x:np.array(jacobian([float(t) for t in x]))/.01) if mode=="analytic_trf" else "2-point"
 result=least_squares(fun,seed,jac=jac,bounds=(-.999,.999),method="trf",
       xtol=1e-13,ftol=1e-13,gtol=1e-13,max_nfev=300)
 return result
def linear_baseline(y):
 # Linearization at neutral. Pseudoinverse solves only first-order approximation.
 j=np.array(A,dtype=float);v=np.array(BIAS)
 return np.clip(np.linalg.lstsq(j,y-v,rcond=None)[0],-.999,.999)
def main():
 results=[]
 for label,truth in (("proxy_A",(.55,-.6,.42,.20)),("proxy_B",(-.4,.55,-.35,-.5))):
  target=np.array(validate_measurements(predict(truth)))
  analytic=fit(target,"analytic_trf")
  finite=fit(target,"finite_diff")
  linear=linear_baseline(target)
  aerr=float(np.linalg.norm(analytic.x-np.array(truth)))
  ferr=float(np.linalg.norm(finite.x-np.array(truth)))
  lerr=float(np.linalg.norm(linear-np.array(truth)))
  are=(float(np.linalg.norm(array_model(analytic.x)-target)))
  fde=(float(np.linalg.norm(array_model(finite.x)-target)))
  le=(float(np.linalg.norm(array_model(linear)-target)))
  sv=np.linalg.svd(np.array(jacobian(truth)),compute_uv=False)
  obs=assess_observability(jacobian(truth),lambda _:list(float(x) for x in sv))
  results.append({"proxy":label,"oracle_truth":truth,"observability":obs,
                  "analytic":{"control_l2_error":aerr,"measured_l2_error_m":are,"nfev":analytic.nfev,"njev":analytic.njev},
                  "finite_difference":{"control_l2_error":ferr,"measured_l2_error_m":fde,"nfev":finite.nfev,"njev":finite.njev},
                  "neutral_linear":{"control_l2_error":lerr,"measured_l2_error_m":le},
                  "semantic_styling_admitted":False})
 good=all(r["observability"]["rank"]==4 and r["analytic"]["control_l2_error"]<1e-7 and
          r["finite_difference"]["control_l2_error"]<1e-7 and
          r["neutral_linear"]["measured_l2_error_m"]>1e-4 and
          r["observability"]["condition_number"]<1000 for r in results)
 report={"schema":"scp.n05.synthetic-inverse-morph.v1","verdict":"PASS_NARROW" if good else "RED",
         "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         "python":platform.python_version(),"packages":{k:importlib.metadata.version(k) for k in ("numpy","scipy")},
         "synthetic_original_profiles_only":True,"real_body_identity_accepted":False,
         "mpfb_mhr_anny_admitted":False,"temporal_styling_identifiable":False,
         "measured_units":"meters","results":results}
 print(json.dumps(report,indent=2,sort_keys=True,allow_nan=False))
 if not good:sys.exit(12)
if __name__=="__main__":main()
