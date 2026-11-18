"""N05 original, rights-clean anthropometric latent/measurement contract in SI meters."""
import math
LATENTS=("height","shoulder_width","hip_width","torso_leg_ratio")
MEASURES=("stature_m","shoulder_span_m","hip_span_m","leg_length_m","torso_length_m","waist_span_m","chest_depth_m","hip_depth_m")
BIAS=(1.67,.42,.36,.83,.51,.31,.23,.22)
A=(
 (.14,0.,0.,.02),
 (0.,.055,0.,.007),
 (0.,.009,.055,0.),
 (.07,0.,0.,-.025),
 (.020,0.,0.,.025),
 (0.,.01,.035,0.),
 (0.,.03,0.,0.),
 (0.,0.,.027,0.),
)
def check_params(x):
 if not isinstance(x,(tuple,list)) or len(x)!=4:raise ValueError("LATENT_LAYOUT")
 if any(type(t) not in (float,int) or not math.isfinite(t) or abs(t)>1.000001 for t in x):raise ValueError("LATENT_OUT_OF_BOUNDS")
 return tuple(float(t) for t in x)
def predict(x):
 x=check_params(x)
 y=[BIAS[i]+sum(a*b for a,b in zip(A[i],x)) for i in range(8)]
 y[3]+=.004*x[0]*x[3]
 y[5]+=.004*x[1]*x[2]
 y[6]+=.003*x[1]*x[1]
 y[7]+=.004*x[2]*x[2]
 return dict(zip(MEASURES,y))
def jacobian(x):
 x=check_params(x)
 j=[list(r) for r in A]
 j[3][0]+=.004*x[3];j[3][3]+=.004*x[0]
 j[5][1]+=.004*x[2];j[5][2]+=.004*x[1]
 j[6][1]+=.006*x[1]
 j[7][2]+=.008*x[2]
 return j
def validate_measurements(values):
 if not isinstance(values,dict) or set(values)!=set(MEASURES):raise ValueError("MEASUREMENT_LAYOUT_OR_LABEL")
 for key in MEASURES:
  v=values[key]
  if type(v) not in (int,float) or not math.isfinite(v) or v<=.05 or v>2.5:raise ValueError("NONFINITE_OR_WRONG_UNITS")
 # Reject unambiguous cm/metre confusion and physically incoherent slices.
 if not (1.2<=values["stature_m"]<=2.2 and .2<=values["leg_length_m"]<=1.4 and
         .2<=values["torso_length_m"]<=1.0 and .2<=values["shoulder_span_m"]<=.75):
  raise ValueError("MEASUREMENT_PLAUSIBILITY_GATE")
 return tuple(float(values[k]) for k in MEASURES)
def assess_observability(j,svd):
 # Morphology-only data cannot infer temporal appearance controls. Do not append
 # makeup/hair/clothing as extra columns or report a five-latent fit.
 if len(j)!=8 or any(len(r)!=4 for r in j):raise ValueError("MORPHOLOGY_RANK_LAYOUT")
 sigma=svd(j)
 if len(sigma)!=4 or any(type(s) not in (float,int) or not math.isfinite(s) for s in sigma):raise ValueError("INVALID_SVD")
 return {"rank":sum(s>1e-9 for s in sigma),"condition_number":sigma[0]/max(sigma[-1],1e-20),
         "time_varying_styling_identifiable":False}
