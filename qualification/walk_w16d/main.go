package main
// W16-D self-authored original geometry falsifiers only. No force, biomechanics,
// real footage, native rigging, camera-lens calibration or identity assertion.
import (
 "encoding/json"
 "errors"
 "fmt"
 "math"
 "os"
)
type V [3]float64
func add(a,b V)V{return V{a[0]+b[0],a[1]+b[1],a[2]+b[2]}}
func sub(a,b V)V{return V{a[0]-b[0],a[1]-b[1],a[2]-b[2]}}
func mul(a V,k float64)V{return V{a[0]*k,a[1]*k,a[2]*k}}
func dot(a,b V)float64{return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]}
func norm(a V)float64{return math.Sqrt(dot(a,a))}
func finite(a V)bool{for _,x:=range a{if math.IsNaN(x)||math.IsInf(x,0){return false}};return true}
func clamp(x float64)float64{if x<0{return 0};if x>1{return 1};return x}
type Foot struct {State string;Heel V;Toe V}
type Frame struct {Frame int;Root V;Hip V;Knee V;Ankle V;Pole V;Foot Foot}
type Actor struct {ID string;Frames []Frame}
type Trace struct {Schema string;Rights string;Basis string;FPSNum int;FPSDen int;Actors []Actor}
type Receipt struct {
 Schema string
 Scope string
 Profile string
 Checks []string
 NegativeControls int
 FrozenGroundTolerance float64
 FrozenStanceSlipTolerance float64
 SweptActorRadius float64
 SyntheticClock string
}
const ground=1e-4 // newly declared synthetic source-scene tolerance
const slip=1e-3 // not derived from real gait or biomechanical evidence
const radius=.25 // deliberately simple witness sphere, NOT mesh collision
func reject(s string)error{return errors.New(s)}
func sweepMinDistance(a0,a1,b0,b1 V)float64{
 p:=sub(a0,b0);v:=sub(sub(a1,a0),sub(b1,b0))
 den:=dot(v,v);t:=0.0
 if den>1e-14{t=clamp(-dot(p,v)/den)}
 return norm(add(p,mul(v,t)))
}
func bendSide(f Frame)float64{
 axis:=sub(f.Ankle,f.Hip)
 length:=norm(axis);if length<1e-10{return 0}
 axis=mul(axis,1/length)
 p:=sub(f.Pole,f.Hip)
 p=sub(p,mul(axis,dot(p,axis)))
 k:=sub(f.Knee,f.Hip)
 k=sub(k,mul(axis,dot(k,axis)))
 if norm(p)<1e-10{return 0}
 return dot(k,mul(p,1/norm(p)))
}
func visible(cam V, focal,near,far float64, target V, blockers []V)bool{
 d:=sub(target,cam)
 if !finite(d)||d[2]<=near||d[2]>=far{return false}
 // symmetric pinhole frustum with focal in source units; no camera calibration.
 if math.Abs(focal*d[0]/d[2])>1||math.Abs(focal*d[1]/d[2])>1{return false}
 for _,b:=range blockers{
  c:=sub(b,cam)
  if c[2]<=near||c[2]>=d[2]{continue}
  t:=dot(c,d)/dot(d,d)
  if t<=0||t>=1{continue}
  if norm(sub(c,mul(d,t)))<radius{return false}
 }
 return true
}
func Check(t Trace)error{
 if t.Schema!="scp.walk_w16d_synthetic_trace.v1"||
 t.Rights!="ORIGINAL_SELF_AUTHORED_SYNTHETIC"||t.Basis!="GLTF_RH_Y_UP_UNCALIBRATED"||
 t.FPSNum!=12||t.FPSDen!=1||len(t.Actors)!=2{return reject("SOURCE_RIGHTS_BASIS_CLOCK_DENIED")}
 ids:=map[string]bool{}
 for _,a:=range t.Actors{
  if a.ID==""||ids[a.ID]||len(a.Frames)!=3{return reject("ACTOR_OR_FRAME_SET_DENIED")}
  ids[a.ID]=true
  for j,f:=range a.Frames{
   if f.Frame!=j*12||!finite(f.Root)||!finite(f.Hip)||!finite(f.Knee)||
    !finite(f.Ankle)||!finite(f.Pole)||!finite(f.Foot.Heel)||!finite(f.Foot.Toe){
     return reject("CLOCK_OR_NONFINITE_DENIED")
   }
   if bendSide(f)<=1e-7{return reject("KNEE_REVERSAL_OR_DEGENERATE_POLE")}
   if f.Foot.State!="stance"&&f.Foot.State!="swing"{return reject("FOOT_STATE_INVALID")}
   if f.Foot.State=="stance"{
    if math.Abs(f.Foot.Heel[1])>ground||math.Abs(f.Foot.Toe[1])>ground{
     return reject("PLANTED_HEEL_TOE_PENETRATION_OR_HOVER")
    }
    if j>0&&a.Frames[j-1].Foot.State=="stance"{
     old:=a.Frames[j-1].Foot
     if norm(sub(old.Heel,f.Foot.Heel))>slip||norm(sub(old.Toe,f.Foot.Toe))>slip{
      return reject("HEEL_OR_TOE_SKATING")
     }
    }
   }
  }
 }
 if !ids["CobaltOriginal"]||!ids["MarigoldOriginal"]{return reject("UNRECOGNIZED_ORIGINAL_ROLE")}
 // Continuous actor roots: midpoint crossing denied even when endpoints clear.
 a,b:=t.Actors[0].Frames,t.Actors[1].Frames
 for j:=1;j<3;j++{
  if sweepMinDistance(a[j-1].Root,a[j].Root,b[j-1].Root,b[j].Root)<2*radius{
   return reject("SWEPT_ACTOR_COLLISION")
  }
 }
 // Deliberately simple camera: require both original actor head points visible
 // without the other actor occluding. No alpha, clothing or mesh occlusion claim.
 cam:=V{0,1.5,-5}
 for j:=0;j<3;j++{
  for i:=0;i<2;i++{
   target:=t.Actors[i].Frames[j].Root
   target[1]+=1.5
   other:=t.Actors[1-i].Frames[j].Root
   other[1]+=1.5
   if !visible(cam,1.25,.1,100,target,[]V{other}){
    return reject("CAMERA_FRUSTUM_OR_ACTOR_OCCLUSION")
   }
  }
 }
 return nil
}
func sample(profile string)Trace{
 left,right:=-1.25,1.25
 if profile=="outward"{left=-1.6;right=1.6}
 mk:=func(id string,x float64)Actor{
  frames:=[]Frame{}
  for j:=0;j<3;j++{
   root:=V{x+.08*float64(j),0,1+.2*float64(j)}
   hip:=add(root,V{0,1.1,0})
   knee:=add(root,V{.25,.62,.15})
   ankle:=add(root,V{.12,.12,.04})
   pole:=add(root,V{.5,.8,.5})
   foot:=Foot{State:"stance",Heel:V{x,0,1},Toe:V{x,0,1.25}}
   if j==2{foot=Foot{State:"swing",Heel:V{x+.10,.08,1.35},Toe:V{x+.1,.08,1.58}}}
   frames=append(frames,Frame{Frame:j*12,Root:root,Hip:hip,Knee:knee,Ankle:ankle,Pole:pole,Foot:foot})
  }
  return Actor{ID:id,Frames:frames}
 }
 return Trace{Schema:"scp.walk_w16d_synthetic_trace.v1",
 Rights:"ORIGINAL_SELF_AUTHORED_SYNTHETIC",Basis:"GLTF_RH_Y_UP_UNCALIBRATED",
 FPSNum:12,FPSDen:1,Actors:[]Actor{mk("CobaltOriginal",left),mk("MarigoldOriginal",right)}}
}
func main(){
 if len(os.Args)!=3{fmt.Fprintln(os.Stderr,"USAGE: w16d forward|outward receipt.json");os.Exit(2)}
 prof:=os.Args[1]
 if prof!="forward"&&prof!="outward"{panic("INVALID_PROFILE")}
 if e:=Check(sample(prof));e!=nil{panic(e)}
 r:=Receipt{Schema:"scp.walk_w16d_geometric_receipt.v1",
 Scope:"ORIGINAL_SYNTHETIC_GEOMETRIC_FALSIFIERS_NOT_NATIVE_RIG_NOT_FORCE_NOT_PRIVATE",
 Profile:prof,Checks:[]string{"heel_toe_stance","continuous_swept_actor_spheres","camera_frustum_proxy","actor_occlusion_proxy","knee_pole_side","source_clock_and_rights"},
 NegativeControls:0,FrozenGroundTolerance:ground,FrozenStanceSlipTolerance:slip,
 SweptActorRadius:radius,SyntheticClock:"12/1"}
 b,e:=json.MarshalIndent(r,"","  ");if e!=nil{panic(e)}
 if e=os.WriteFile(os.Args[2],append(b,10),0644);e!=nil{panic(e)}
 fmt.Println("W16D_GEOMETRIC_SOURCE_ONLY_PASS",prof)
}
