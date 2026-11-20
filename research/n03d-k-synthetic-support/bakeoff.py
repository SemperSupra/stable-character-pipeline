"""Actual bounded SciPy five-link support-target solver on original known-answer synthetic fixtures."""
import hashlib,importlib.metadata,json,math,platform,sys
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from planar_support import LINKS,positions,jacobian,finite_angles
N=7
TRUE=(.20,-.28,.25,-.19,.02)
def problem():
 p=(.0,sum(L*math.cos(sum(TRUE[:j+1])) for j,L in enumerate(LINKS))+.06)
 anchors=np.array(positions(TRUE,p),dtype=float)
 source=[]
 for i in range(N):
  source.append([TRUE[k]+.05*math.sin((i+2)*(k+1)*.7)+.035*math.cos((i+1)*(k+2)*.5) for k in range(5)])
 return p,anchors,np.asarray(source)
def fit(p,target,sources,mode):
 from planar_support import fk
 if mode not in ("bone_tail_only","heel_toe_sole"):raise ValueError("UNKNOWN_CONTACT_TARGET")
 def fun(xs):
  q=xs.reshape(N,5)
  res=[]
  for i in range(N):
   if mode=="heel_toe_sole":
    v=np.array(positions(q[i].tolist(),p))
    res.extend(((v-target)/.005).tolist())
   else:
    x,z,_,_=fk(q[i].tolist(),p)
    # The foot-tail endpoint target is the midpoint of TRUE heel+toe (z corrected).
    target_tip=np.array([(target[0]+target[2])/2,(target[1]+target[3])/2+.06])
    res.extend(((np.array([x,z])-target_tip)/.005).tolist())
  # Required temporal/source prior; DOES NOT invent joint limits for a real person.
  res.extend(((q-sources)/.25).ravel().tolist())
  res.extend(((q[1:]-q[:-1])/.13).ravel().tolist())
  return np.asarray(res)
 raw=least_squares(fun,sources.ravel(),bounds=(-.9*np.ones(N*5),.9*np.ones(N*5)),
                   method="trf",max_nfev=300,xtol=1e-11,gtol=1e-11,ftol=1e-11)
 poses=raw.x.reshape(N,5)
 errors=[float(np.max(np.abs(np.array(positions(row.tolist(),p))-target))) for row in poses]
 depths=[float(min(positions(row.tolist(),p)[1],positions(row.tolist(),p)[3])) for row in poses]
 pitches=[float(sum(row)) for row in poses]
 return {"source_angles":sources.tolist(),"candidate_angles":poses.tolist(),
         "max_support_coordinate_error_m":max(errors),
         "max_floor_penetration_m":max(0.,-min(depths)),
         "max_abs_foot_pitch_rad":max(map(abs,pitches)),
         "max_frame_joint_delta_rad":float(np.max(np.abs(np.diff(poses,axis=0)))),
         "max_source_joint_change_rad":float(np.max(np.abs(poses-sources))),
         "status":int(raw.status),"nfev":raw.nfev,"cost":float(raw.cost)}
def main():
 p,target,source=problem()
 base=fit(p,target,source,"bone_tail_only")
 candidate=fit(p,target,source,"heel_toe_sole")
 good=(base["status"]>0 and candidate["status"]>0 and
       candidate["max_support_coordinate_error_m"]<.010 and
       candidate["max_floor_penetration_m"]<.010 and
       candidate["max_abs_foot_pitch_rad"]<.08 and
       candidate["max_support_coordinate_error_m"]<base["max_support_coordinate_error_m"]*.75 and
       candidate["max_source_joint_change_rad"]<.4)
 report={"schema":"scp.n03d-k.synthetic-support-optimizer.v1",
   "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
   "python":platform.python_version(),"numpy":importlib.metadata.version("numpy"),
   "scipy":importlib.metadata.version("scipy"),
   "fixture":"ORIGINAL_SYNTHETIC_PLANAR_FIVE_LINK_KNOWN_TRUTH",
   "frames":N,"correct_support_coordinates_m":target.tolist(),
   "truth_5_joint_radians":TRUE,"pelvis_world_m":p,
   "foot_tail_only":base,"heel_and_toe":candidate,
   "verdict":"PASS_NARROW" if good else "RED",
   "real_mpfb_bone_lengths_or_knee_axes_calibrated":False,
   "source_cc0_material_support_observed":False,
   "ground_contact_accepted":False,"mvp_accepted":False,"release_authorized":False}
 print(json.dumps(report,sort_keys=True,indent=2,allow_nan=False))
 if not good:sys.exit(12)
if __name__=="__main__":main()
