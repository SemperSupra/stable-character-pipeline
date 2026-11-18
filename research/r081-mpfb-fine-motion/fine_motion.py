"""R081 source-safe 24fps two-character gait and damped tissue ACTUATOR controls.
Not measured human walking, contact, FEM, or source-person fidelity.
"""
import math
FPS=24
FRAMES=144
SAMPLE_RATE=240
STEPPER_HZ=1.25
SOURCES=("AsterOriginal","JuniperOriginal")
PHASES=(0.0,0.4)
def clip(v,lo,hi):
 if not math.isfinite(v):raise ValueError("NONFINITE_CONTROL")
 return max(lo,min(hi,v))
def time(frame):
 if type(frame) is not int or frame<0 or frame>=FRAMES:raise ValueError("FRAME_OUT_OF_RANGE")
 return frame/FPS
def roots(frame):
 u=frame/(FRAMES-1)
 return (-3.35+2.56*u,3.35-2.56*u)
def pose(frame,phase):
 t=time(frame);p=2*math.pi*STEPPER_HZ*t+phase
 return {"upperleg_L":.34*math.sin(p),"upperleg_R":-.34*math.sin(p),
         "lowerleg_L":.13+.38*max(0,math.sin(p+math.pi)),"lowerleg_R":.13+.38*max(0,math.sin(p)),
         "heel_roll_L":-.13*math.sin(p),"heel_roll_R":.13*math.sin(p),
         "arm_swing_L":-.18*math.sin(p),"arm_swing_R":.18*math.sin(p),
         "bob_m":.006*(1-math.cos(2*p)),"sway_m":.007*math.sin(p),
         "root_x_m":roots(frame)[0]}
def tissue_series(phase):
 # Three bounded underdamped lumped oscillators at 240 Hz driven by step impulses.
 # Values are signed relative controls for native ±2 mm morph pairs, NOT tissue pressures.
 state=[[0.0,0.0] for _ in range(3)]
 out=[];dt=1/SAMPLE_RATE
 settings=((2.7,.7,.35),(3.8,.9,.26),(2.1,.8,.22))
 for frame in range(FRAMES):
  for j in range(SAMPLE_RATE//FPS):
   t=(frame*(SAMPLE_RATE//FPS)+j)*dt
   p=2*math.pi*STEPPER_HZ*t+phase
   pulse=max(0,math.cos(2*p))**10
   for k,(freq,damping,strength) in enumerate(settings):
    w=2*math.pi*freq;x,v=state[k]
    force=(pulse-.12)*strength
    v+=dt*(force-2*damping*w*v-w*w*x)
    x+=dt*v
    state[k]=[x,v]
  out.append(tuple(clip(140*x,-.9,.9) for x,_ in state))
 return out
def validate():
 assert (FPS,FRAMES,SAMPLE_RATE)==(24,144,240)
 assert abs(roots(0)[1]-roots(0)[0]-6.7)<1e-9
 assert abs(roots(FRAMES-1)[1]-roots(FRAMES-1)[0]-1.58)<1e-9
 for phase in PHASES:
  data=tissue_series(phase)
  if len(data)!=FRAMES or max(abs(v) for sample in data for v in sample)<=0:raise ValueError("TISSUE_NO_MOTION")
  for f in range(FRAMES):
   r=pose(f,phase)
   if not all(math.isfinite(v) for v in r.values()):raise ValueError("NONFINITE_KINEMATICS")
 return True
