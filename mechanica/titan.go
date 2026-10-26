package main

// The Iron Atlas is an original, synthetic articulated giant walking machine.
// Mechanical blockout only: controls are keyed; contact dynamics are not solved.
import "fmt"

func addTitan(s *Builder) {
 const prefix="titan/iron-atlas"
 olive:=s.material("titan/olive-armor",V{.31,.36,.30})
 armor:=s.material("titan/charcoal-armor",V{.11,.15,.16})
 steel:=s.material("titan/brushed-steel",V{.51,.56,.57})
 jointmat:=s.material("titan/hinge-dark",V{.075,.085,.09})
 gold:=s.material("titan/hazard-amber",V{.92,.43,.085})
 glass:=s.material("titan/cockpit-glass",V{.12,.34,.41})
 red:=s.material("titan/sensor-red",V{.73,.13,.095})

 root,rig:=s.rig(prefix,V{12.5,0,0})
 // Broad pelvis with two independently articulated legs.
 s.part(prefix+"/pelvis","box",root,V{0,0,5.13},V{1.9,3.4,1.1},armor)
 s.part(prefix+"/hip-armor-front","box",root,V{.98,0,5.10},V{.22,2.5,.72},olive)
 for _,side:=range []int{-1,1} {
  sn,sy:="port",-1.
  if side>0 {sn,sy="starboard",1}
  tag:=prefix+"/"+sn
  hip:=s.joint(rig,tag+"/hip-pitch","revolute",root,V{0,sy*1.25,5.05},V{0,1,0},-32,32)
  s.part(tag+"/hip-housing","ellipsoid",hip,V{0,0,0},V{1.1,1.13,1.04},steel)
  s.part(tag+"/upper-leg","box",hip,V{-.17,0,-1.07},V{1.35,1.08,2.15},olive)
  s.part(tag+"/upper-leg-front-plate","box",hip,V{.58,0,-.97},V{.20,.88,1.48},armor)
  s.part(tag+"/thigh-piston","cylinder-y",hip,V{-.6,0,-1.28},V{.54,.68,.54},steel)
  knee:=s.joint(rig,tag+"/knee-pitch","revolute",hip,V{-.22,0,-2.08},V{0,1,0},-8,56)
  s.part(tag+"/knee-joint","cylinder-y",knee,V{},V{.77,1.31,.77},jointmat)
  s.part(tag+"/lower-leg","box",knee,V{-.16,0,-.94},V{1.22,1.06,1.95},olive)
  s.part(tag+"/shin-armor","box",knee,V{.49,0,-1.05},V{.24,.95,1.58},armor)
  ankle:=s.joint(rig,tag+"/ankle-pitch","revolute",knee,V{-.18,0,-1.91},V{0,1,0},-28,28)
  s.part(tag+"/ankle-housing","ellipsoid",ankle,V{},V{.88,1.03,.62},steel)
  s.part(tag+"/foot","box",ankle,V{.52,0,-.27},V{2.02,1.45,.47},armor)
  s.part(tag+"/toe-armor","box",ankle,V{1.39,0,-.30},V{.42,1.29,.33},olive)
  s.part(tag+"/heel","box",ankle,V{-.36,0,-.28},V{.55,1.35,.46},steel)
  if side<0 {
   s.animate(hip,V{0,1,0},0,21,21,-12,0)
   s.animate(knee,V{0,1,0},0,26,26,11,0)
   s.animate(ankle,V{0,1,0},0,-19,-19,3,0)
  }else{
   s.animate(hip,V{0,1,0},0,-13,-13,17,0)
   s.animate(knee,V{0,1,0},0,10,10,25,0)
   s.animate(ankle,V{0,1,0},0,8,8,-17,0)
  }
 }
 torsoYaw:=s.joint(rig,prefix+"/torso-yaw","revolute",root,V{0,0,5.65},V{0,0,1},-55,55)
 torsoPitch:=s.joint(rig,prefix+"/torso-pitch","revolute",torsoYaw,V{},V{0,1,0},-15,15)
 s.part(prefix+"/core","box",torsoPitch,V{0,0,1.19},V{2.54,3.68,2.75},armor)
 s.part(prefix+"/front-armor","box",torsoPitch,V{1.29,0,1.34},V{.35,3.38,2.35},olive)
 s.part(prefix+"/chest-bevel","ellipsoid",torsoPitch,V{1.41,0,1.66},V{.38,2.73,.86},olive)
 s.part(prefix+"/backpack","box",torsoPitch,V{-1.25,0,1.53},V{.91,2.90,2.78},steel)
 for _,sy:=range []float64{-1,1}{
  s.part(fmt.Sprintf("%s/back-vent-%v",prefix,sy),"box",torsoPitch,V{-1.74,sy*.76,1.6},V{.10,.7,1.76},jointmat)
  s.part(fmt.Sprintf("%s/chest-mark-%v",prefix,sy),"box",torsoPitch,V{1.52,sy*.7,1.42},V{.07,.19,1.09},gold)
 }
 s.animate(torsoYaw,V{0,0,1},0,20,-18,12,0)
 s.animate(torsoPitch,V{0,1,0},0,-5,9,-6,0)

 headYaw:=s.joint(rig,prefix+"/cockpit-yaw","revolute",torsoPitch,V{.82,0,2.59},V{0,0,1},-70,70)
 headPitch:=s.joint(rig,prefix+"/cockpit-pitch","revolute",headYaw,V{},V{0,1,0},-20,25)
 s.part(prefix+"/cockpit-shell","box",headPitch,V{.23,0,.38},V{1.50,1.47,.94},olive)
 s.part(prefix+"/cockpit-visor","ellipsoid",headPitch,V{1.00,0,.47},V{.46,1.19,.60},glass)
 s.part(prefix+"/cockpit-roof","box",headPitch,V{.14,0,.97},V{1.17,1.56,.17},armor)
 s.part(prefix+"/optical-eye","ellipsoid",headPitch,V{1.19,0,.45},V{.12,.19,.16},red)
 s.animate(headYaw,V{0,0,1},0,-29,31,-14,0)
 s.animate(headPitch,V{0,1,0},0,-12,14,6,0)

 // Shoulder stations; weapon-side support and right-side manipulator are distinct.
 for _,side:=range []int{-1,1}{
  sn,sy:="port",-1.
  if side>0{sn,sy="starboard",1}
  tag:=prefix+"/"+sn
  shoulder:=s.joint(rig,tag+"/shoulder-roll","revolute",torsoPitch,V{0,sy*2.06,1.75},V{1,0,0},-35,45)
  s.part(tag+"/shoulder-drum","cylinder-y",shoulder,V{},V{1.14,1.39,1.14},steel)
  s.part(tag+"/shoulder-armor","box",shoulder,V{.05,sy*.53,.15},V{1.72,1.3,1.33},olive)
  s.part(tag+"/upper-arm","box",shoulder,V{-.18,sy*.79,-.81},V{1.20,1.08,1.60},armor)
  elbow:=s.joint(rig,tag+"/elbow-pitch","revolute",shoulder,V{0,sy*.82,-1.49},V{0,1,0},-75,85)
  s.part(tag+"/elbow-bearing","cylinder-y",elbow,V{},V{.87,.98,.87},steel)
  s.part(tag+"/forearm","box",elbow,V{.15,0,-.63},V{1.02,.92,1.36},olive)
  if side<0 {
   aim:=s.joint(rig,tag+"/cannon-elevation","revolute",elbow,V{.52,0,-1.12},V{0,1,0},-20,35)
   s.part(tag+"/cannon-housing","box",aim,V{.46,0,-.04},V{1.38,.94,.96},armor)
   s.part(tag+"/cannon-barrel","cylinder-x",aim,V{1.65,0,0},V{2.8,.44,.44},steel)
   s.part(tag+"/muzzle-collar","cylinder-x",aim,V{2.97,0,0},V{.28,.65,.65},jointmat)
   spin:=s.joint(rig,tag+"/barrel-ring-spin","continuous",aim,V{2.86,0,0},V{1,0,0},-1e6,1e6)
   s.part(tag+"/barrel-rotor","box",spin,V{0,0,.32},V{.21,.15,.55},gold)
   s.animate(shoulder,V{1,0,0},0,22,22,-10,0)
   s.animate(elbow,V{0,1,0},0,-38,-38,15,0)
   s.animate(aim,V{0,1,0},0,15,-17,10,0)
   s.spin(spin,V{1,0,0},1.75)
  }else{
   wrist:=s.joint(rig,tag+"/wrist-yaw","revolute",elbow,V{.15,0,-1.32},V{0,0,1},-90,90)
   s.part(tag+"/palm","box",wrist,V{.13,0,-.14},V{.74,.73,.48},steel)
   for _,finger:=range []int{-1,1}{
    fy:=float64(finger)
    j:=s.joint(rig,fmt.Sprintf("%s/claw-finger-%d",tag,finger),"revolute",wrist,V{.25,fy*.38,-.21},V{1,0,0},-52,52)
    s.part(fmt.Sprintf("%s/claw-tine-%d",tag,finger),"box",j,V{.35,0,-.38},V{.72,.25,.79},armor)
    angle:=35.;if finger<0{angle=-35}
    s.animate(j,V{1,0,0},0,angle,angle,0,0)
   }
   s.animate(shoulder,V{1,0,0},0,-26,-26,18,0)
   s.animate(elbow,V{0,1,0},0,48,48,-22,0)
   s.animate(wrist,V{0,0,1},0,35,-30,15,0)
  }
 }
 // Shoulder pods are articulated; individual tubes are *decorative* (no ordnance simulation).
 for _,side:=range []int{-1,1}{
  sn,sy:="port",-1.
  if side>0{sn,sy="starboard",1}
  tag:=prefix+"/"+sn
  pod:=s.joint(rig,tag+"/pod-elevation","revolute",torsoPitch,V{-.40,sy*1.45,2.68},V{0,1,0},-8,42)
  s.part(tag+"/pod-body","box",pod,V{- .17,sy*.18,.52},V{1.40,1.32,1.12},olive)
  for row:=0;row<2;row++{for col:=0;col<3;col++{
   y:=sy*.18+(float64(col)-1)*.32
   z:=.32+float64(row)*.37
   s.part(fmt.Sprintf("%s/pod-cell-%d-%d",tag,row,col),"cylinder-x",pod,V{.56,y,z},V{.10,.22,.22},jointmat)
   s.part(fmt.Sprintf("%s/pod-marker-%d-%d",tag,row,col),"ellipsoid",pod,V{.63,y,z},V{.08,.12,.12},red)
  }}
  s.animate(pod,V{0,1,0},0,25,25,0,0)
 }
 hatch:=s.joint(rig,prefix+"/maintenance-hatch","revolute",torsoPitch,V{-1.75,-.75,2.15},V{0,1,0},-85,8)
 s.part(prefix+"/maintenance-panel","box",hatch,V{-.05,.1,-.46},V{.12,1.28,.91},olive)
 s.animate(hatch,V{0,1,0},0,-64,-64,0,0)
 radar:=s.joint(rig,prefix+"/sensor-mast-yaw","revolute",torsoPitch,V{-1.02,0,2.77},V{0,0,1},-135,135)
 s.part(prefix+"/sensor-mast","cylinder-y",radar,V{0,0,.42},V{.12,.12,.87},steel)
 s.part(prefix+"/sensor-cluster","ellipsoid",radar,V{.13,0,.85},V{.34,.38,.25},red)
 s.animate(radar,V{0,0,1},0,90,-90,25,0)
}
