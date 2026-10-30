package main
// W16-B3: original synthetic dual-leg v3 source, NOT a W13 timed track.
import("encoding/json";"fmt";"math";"os")
type V [3]float64
type Leg struct { ID string; Parent string; Knee V; Ankle V; UpperWorld [4]float64; LowerWorld [4]float64; Contact string }
type Frame struct { Frame int; TimeNum int; TimeDen int; Root V; Legs []Leg }
type Actor struct { ID string; Rest []string; Frames []Frame }
type Packet struct { Schema string; Rights string; OriginSHA string; Basis string; QuatOrder string; ClockOrigin string; FPSNum int; FPSDen int; Profile string; Actors []Actor }
type Receipt struct { Schema string; Profile string; Observations int; MaxIKError float64; SourceOnly bool; Contact string }
func add(a,b V)V{return V{a[0]+b[0],a[1]+b[1],a[2]+b[2]}}
func sub(a,b V)V{return V{a[0]-b[0],a[1]-b[1],a[2]-b[2]}}
func mul(a V,s float64)V{return V{a[0]*s,a[1]*s,a[2]*s}}
func dot(a,b V)float64{return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]}
func length(a V)float64{return math.Sqrt(dot(a,a))}
func unit(a V)V{n:=length(a);return mul(a,1/n)}
func knee(hip,ankle,pole V)V{
 diff:=sub(ankle,hip);d:=length(diff)
 if d<=0||d>=1.2{panic("UNREACHABLE_SOURCE_TARGET")}
 axis:=unit(diff);pv:=sub(pole,hip);pv=sub(pv,mul(axis,dot(pv,axis)));if length(pv)<1e-10{panic("POLE_DEGENERATE")}
 return add(hip,add(mul(axis,d/2),mul(unit(pv),math.Sqrt(.36-d*d/4))))
}
func quaternion(from,to V)[4]float64{
 a,b:=unit(from),unit(to);co:=dot(a,b)
 if co>1-1e-12{return [4]float64{0,0,0,1}}
 cr:=V{a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]}
 q:=[4]float64{cr[0],cr[1],cr[2],1+co}
 n:=math.Sqrt(q[0]*q[0]+q[1]*q[1]+q[2]*q[2]+q[3]*q[3])
 if n<1e-10{panic("ANTIPARALLEL_UNHANDLED")}
 for i:=range q{q[i]/=n};return q
}
func makePacket(profile string)(Packet,Receipt,error){
 if profile!="forward"&&profile!="outward"{return Packet{},Receipt{},fmt.Errorf("PROFILE")}
 frames:=[]int{0,12,24,36,48,60,71}
 actors:=[]Actor{};max:=0.
 for _,a:=range []struct{name string;x float64}{{"CobaltOriginal",-1.65},{"MarigoldOriginal",1.65}}{
  obj:=Actor{ID:a.name,Rest:[]string{"LeftUpper","LeftLower:LeftUpper","RightUpper","RightLower:RightUpper"}}
  for _,f:=range frames{
   frac:=float64(f)/71;direction:=1.;if profile=="outward"{direction= -1}
   root:=V{a.x,direction*.16*frac,0}
   frame:=Frame{Frame:f,TimeNum:f,TimeDen:12,Root:root}
   for _,leg:=range []struct{name string;sign float64}{{"Left",-1},{"Right",1}}{
    hip:=V{a.x+leg.sign*.22,root[1],1.4}
    endpoint:=V{hip[0],root[1],.2};j:=V{hip[0],root[1],.8}
    if f!=0{
     phase:=2*math.Pi*frac;if leg.sign<0{phase+=math.Pi}
     endpoint=V{hip[0],root[1]+.18*math.Sin(phase),.25+.04*math.Max(0,math.Cos(phase))}
     j=knee(hip,endpoint,add(hip,V{leg.sign*.36,.48,-.42}))
    }
    residual:=math.Max(math.Abs(length(sub(j,hip))-.6),math.Abs(length(sub(endpoint,j))-.6))
    if residual>max{max=residual}
    if residual>1e-8{return Packet{},Receipt{},fmt.Errorf("IK_SEGMENT_INVARIANT")}
    frame.Legs=append(frame.Legs,Leg{leg.name,leg.name+"Upper",j,endpoint,
      quaternion(V{0,0,-1},sub(j,hip)),quaternion(V{0,0,-1},sub(endpoint,j)),"unknown"})
   }
   obj.Frames=append(obj.Frames,frame)
  }
  actors=append(actors,obj)
 }
 p:=Packet{"scp.walk_dual_leg_motion.v3","ORIGINAL_SELF_AUTHORED_SYNTHETIC",
  "e0a42b8d5dfe23334486ff195ac90fe6b7d3a199","BLENDER_RH_Z_UP_SOURCE",
  "GLTF_XYZW_COMPONENTS_Z_UP_FRAME","SYNTHETIC_ZERO_NO_MEASURED_CLOCK",12,1,profile,actors}
 if e:=Validate(p);e!=nil{return Packet{},Receipt{},e}
 return p,Receipt{"scp.walk_b3_receipt.v1",profile,28,max,true,"ALL_UNKNOWN"},nil
}
func Validate(p Packet)error{
 if p.Schema!="scp.walk_dual_leg_motion.v3"||p.Rights!="ORIGINAL_SELF_AUTHORED_SYNTHETIC"||
 p.OriginSHA!="e0a42b8d5dfe23334486ff195ac90fe6b7d3a199"||
 p.Basis!="BLENDER_RH_Z_UP_SOURCE"||p.QuatOrder!="GLTF_XYZW_COMPONENTS_Z_UP_FRAME"||
 p.ClockOrigin!="SYNTHETIC_ZERO_NO_MEASURED_CLOCK"||p.FPSNum!=12||p.FPSDen!=1||
 len(p.Actors)!=2{return fmt.Errorf("SCHEMA_RIGHTS_CLOCK_BASIS")}
 for i,a:=range p.Actors{
  if a.ID!=[]string{"CobaltOriginal","MarigoldOriginal"}[i]||len(a.Rest)!=4||len(a.Frames)!=7{return fmt.Errorf("ACTOR_REST")}
  for fi,f:=range a.Frames{
   if f.Frame!=[]int{0,12,24,36,48,60,71}[fi]||f.TimeNum!=f.Frame||f.TimeDen!=12||len(f.Legs)!=2{return fmt.Errorf("FRAME_CLOCK")}
   for j,l:=range f.Legs{
    if l.ID!=[]string{"Left","Right"}[j]||l.Parent!=l.ID+"Upper"||l.Contact!="unknown"||
    math.IsNaN(l.Ankle[0])||math.IsNaN(l.Knee[0]){return fmt.Errorf("LEG_CONTACT_OR_PARENT")}
    for _,q:=range [][4]float64{l.UpperWorld,l.LowerWorld}{
     s:=0.;for _,v:=range q{if math.IsNaN(v)||math.IsInf(v,0){return fmt.Errorf("NONFINITE_QUAT")};s+=v*v}
     if math.Abs(s-1)>1e-6{return fmt.Errorf("BAD_QUAT_NORM")}
    }
   }
  }
 }
 return nil
}
func main(){
 if len(os.Args)!=4{panic("usage: b3 profile typed.json receipt.json")}
 p,r,e:=makePacket(os.Args[1]);if e!=nil{panic(e)}
 data,_:=json.MarshalIndent(p,"","  ");if e=os.WriteFile(os.Args[2],append(data,10),0644);e!=nil{panic(e)}
 data,_=json.MarshalIndent(r,"","  ");if e=os.WriteFile(os.Args[3],append(data,10),0644);e!=nil{panic(e)}
 fmt.Println("W16B3_TYPED_TWO_LEG_PASS",r.MaxIKError,r.Observations)
}
