#!/usr/bin/env python3
"""Original-authored two-actor 72-frame articulated surrogate ground truth.
Pure Python stdlib. No private figures, photos, measured mocap or external assets.
"""
import argparse,hashlib,json,math,pathlib

SCHEMA="scp.shadow.original-two-actor.v1"
FPS=12
FRAMES=72
PERIOD=1.6
SPEED=.42
WALK_END=5.
THIGH=.49
SHIN=.48
STANCE=.6
ACTORS=("CobaltOriginal","MarigoldOriginal")

def smooth(u):
 u=max(0.,min(1.,u))
 return u*u*(3.-2.*u)

def v(x,y,z):
 return [round(float(x),9),round(float(y),9),round(float(z),9)]

def step_foot(t,side):
 offset=0. if side=="left" else .5
 active=min(t,WALK_END)
 phase=(active/PERIOD+offset)%1.
 half=SPEED*PERIOD*STANCE/2.
 if phase<STANCE:
  y=half-SPEED*PERIOD*phase
  lift=0.
  contact=True
 else:
  u=(phase-STANCE)/(1.-STANCE)
  y=-half+2.*half*smooth(u)
  lift=.1*math.sin(math.pi*u)
  contact=False
 if t>WALK_END:
  lift*=1.-smooth((t-WALK_END)/.4)
  contact=lift<1e-6
 return y,max(0.,lift),bool(contact)

def solve_leg(hip,ankle):
 # Exact two-link planar IK in local forward/up plane.
 dy=ankle[1]-hip[1];dz=ankle[2]-hip[2]
 distance=math.hypot(dy,dz)
 if distance>=THIGH+SHIN or distance<=abs(THIGH-SHIN):
  raise ValueError("UNREACHABLE_OR_COLLAPSED_SYNTHETIC_IK")
 a=(THIGH*THIGH-SHIN*SHIN+distance*distance)/(2.*distance)
 h=math.sqrt(max(0.,THIGH*THIGH-a*a))
 # forward-bending, never a mirrored or discontinuous joint sign
 py=-dz/distance;pz=dy/distance
 return (hip[0],hip[1]+a*dy/distance+h*py,hip[2]+a*dz/distance+h*pz)

def character(actor,t):
 sign=1. if actor==ACTORS[0] else -1.
 root=sign*(-3.2+SPEED*min(t,WALK_END))
 # local forward is positive y, lateral is x. Two actors face each other.
 def world(p):
  return v(root+sign*p[1],p[0],p[2])
 bones={}
 feet={}
 def bone(name,head,tail):
  bones[name]={"head":world(head),"tail":world(tail)}
 pelvic=(0.,0.,.99)
 chest=(0.,0.,1.38)
 neck=(0.,0.,1.56)
 skull=(0.,0.,1.76)
 bone("torso",pelvic,chest)
 bone("neck",chest,neck)
 bone("head",neck,skull)
 for side, lateral in (("left",-.115),("right",.115)):
  y,lift,contact=step_foot(t,side)
  hip=(lateral,0.,.99)
  ankle=(lateral,y,.10+lift)
  knee=solve_leg(hip,ankle)
  toe=(lateral,y+.22,.045+lift)
  bone(side+"_thigh",hip,knee)
  bone(side+"_shin",knee,ankle)
  bone(side+"_foot",ankle,toe)
  # arm swing counterphases with its own leg; original, not captured gait
  wave=math.sin(2.*math.pi*t/PERIOD+(0. if side=="left" else math.pi))
  shoulder=(lateral*2.1,0.,1.45)
  elbow_y=-.095*wave
  elbow_x=lateral*2.65
  elbow_z=shoulder[2]-math.sqrt(.30**2-(elbow_x-shoulder[0])**2-elbow_y**2)
  elbow=(elbow_x,elbow_y,elbow_z)
  wrist_x=lateral*2.85
  wrist_y=elbow_y-.12*wave
  wrist_z=elbow_z-math.sqrt(.27**2-(wrist_x-elbow_x)**2-(wrist_y-elbow_y)**2)
  wrist=(wrist_x,wrist_y,wrist_z)
  bone(side+"_upperarm",shoulder,elbow)
  bone(side+"_forearm",elbow,wrist)
  feet[side]={"ankle":world(ankle),"contact":contact,"lift_m":round(lift,9)}
 return {"root_x_m":round(root,9),"bones":bones,"feet":feet}

def produce():
 records=[]
 for frame in range(FRAMES):
  t=frame/FPS
  records.append({"frame":frame,"time_seconds":round(t,9),
    "actors":{actor:character(actor,t) for actor in ACTORS}})
 return {"schema":SCHEMA,"source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
   "private_r009":"HELD_NOT_ACCEPTED","measured_human":"NOT_ADMITTED",
   "authentic_identity":"NOT_VERIFIED","stage":"SYNTHETIC_SURROGATE_NOT_BIOPHYSICS",
   "fps":FPS,"frame_count":FRAMES,"duration_clock_seconds":6.,
   "frame_time_last_seconds":round((FRAMES-1)/FPS,9),
   "actor_ids":list(ACTORS),"bone_count_per_actor":13,
   "cameras":{"front":{"position":[0.,-7.2,3.4],"target":[0.,0.,1.2]},
              "oblique":{"position":[5.,-6.,3.7],"target":[0.,0.,1.2]}},
   "geometry":{"source_thigh_length_m":THIGH,"source_shin_length_m":SHIN,
    "stance_fraction":STANCE,"cycle_seconds":PERIOD,
    "root_speed_m_s":SPEED,"root_stop_seconds":WALK_END},
   "frames":records}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--out")
 p.add_argument("--capabilities",action="store_true")
 a=p.parse_args()
 if a.capabilities:
  print(json.dumps({"schema":SCHEMA,"actions":["capabilities","generate_authored_unprotected"],
   "author":"ORIGINAL_SYNTHETIC","rights":"SELF_AUTHORED_FIXTURE_ONLY",
   "private_r009":"HELD_NOT_ACCEPTED"},sort_keys=True));return
 if not a.out:p.error("--out must name a NEW output file")
 data=json.dumps(produce(),sort_keys=True,separators=(",",":")).encode()+b"\n"
 with pathlib.Path(a.out).open("xb") as out:out.write(data)
 print(json.dumps({"schema":"scp.shadow.producer.receipt.v1","trace_sha256":hashlib.sha256(data).hexdigest(),
   "bytes":len(data),"actors":2,"frames":FRAMES,"private_r009":"HELD"}))
if __name__=="__main__":main()
