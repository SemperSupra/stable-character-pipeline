package main
// W16-B2: W13 independent spatial snapshots lowered to W16-A structural
// 3-frame synthetic provenance packet, NOT observed temporal human motion.
import (
 "crypto/sha256"
 "encoding/json"
 "errors"
 "fmt"
 "math"
 "os"
 "../walk_w16b/solvera"
 "./typed"
)
type Vec=[3]float64
type Quaternion=[4]float64 // glTF XYZW
type Ledger struct {
 Schema string
 Status string
 SourceFixtureSHA256 string
 DerivedPacketSHA256 string
 OriginalW13ACommit string
 StructuralW16ACommit string
 SpatialCaseIDs []string
 MaxAnalyticFKError float64
 MaxBasisRoundtripError float64
 SyntheticTimeOnly bool
 NativeSourceTimeAdmitted bool
 ActualWeightedSkinAdmitted bool
 SourceAndRightsPolicy string
}
const originA="1967886686d008f8db33e5c90328928d5fe944ed"
const originW16="0b283718183dff20313c3ba4517830245267c053"
func plus(a,b Vec)Vec{return Vec{a[0]+b[0],a[1]+b[1],a[2]+b[2]}}
func minus(a,b Vec)Vec{return Vec{a[0]-b[0],a[1]-b[1],a[2]-b[2]}}
func times(a Vec,v float64)Vec{return Vec{a[0]*v,a[1]*v,a[2]*v}}
func dot(a,b Vec)float64{return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]}
func cross(a,b Vec)Vec{return Vec{a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]}}
func norm(a Vec)float64{return math.Sqrt(dot(a,a))}
func unit(a Vec)(Vec,error){n:=norm(a);if !(n>1e-12){return Vec{},errors.New("ZERO_VECTOR")};return times(a,1/n),nil}
func normalized(q Quaternion)(Quaternion,error){
 n:=0.;for _,a:=range q{if math.IsNaN(a)||math.IsInf(a,0){return Quaternion{},errors.New("NONFINITE_QUAT")};n+=a*a}
 if !(n>1e-12){return Quaternion{},errors.New("ZERO_QUAT")}
 n=math.Sqrt(n);for i:=range q{q[i]/=n};return q,nil
}
func between(a,b Vec)(Quaternion,error){
 u,e:=unit(a);if e!=nil{return Quaternion{},e};v,e:=unit(b);if e!=nil{return Quaternion{},e}
 c:=math.Max(-1,math.Min(1,dot(u,v)))
 if c>1-1e-12{return Quaternion{0,0,0,1},nil}
 if c< -1+1e-12{
  basis:=Vec{1,0,0};if math.Abs(u[0])>.9{basis=Vec{0,0,1}}
  axis,e:=unit(cross(u,basis));if e!=nil{return Quaternion{},e}
  return Quaternion{axis[0],axis[1],axis[2],0},nil
 }
 cr:=cross(u,v)
 return normalized(Quaternion{cr[0],cr[1],cr[2],1+c})
}
func multiply(a,b Quaternion)Quaternion{
 ax,ay,az,aw:=a[0],a[1],a[2],a[3];bx,by,bz,bw:=b[0],b[1],b[2],b[3]
 return Quaternion{aw*bx+ax*bw+ay*bz-az*by,aw*by-ay*bw+az*bx-ax*bz,aw*bz+az*bw+ax*by-ay*bx,aw*bw-ax*bx-ay*by-az*bz}
}
func inverse(q Quaternion)Quaternion{return Quaternion{-q[0],-q[1],-q[2],q[3]}}
func rotate(q Quaternion,v Vec)Vec{
 qv:=Vec{q[0],q[1],q[2]};t:=times(cross(qv,v),2)
 return plus(v,plus(times(t,q[3]),cross(qv,t)))
}
func asQ(q Quaternion)typed.Q{return typed.Q(q)}
func asV(v Vec)typed.V{return typed.V(v)}
func ptr(v int)*int{return &v}
// Roundtrip to explicit Blender Z-up synthetic intermediate and then GLTF Y-up.
// Not proof of native Blender source or basis calibration.
func toBlender(v Vec)Vec{return Vec{v[0],-v[2],v[1]}}
func toGLTF(v Vec)Vec{return Vec{v[0],v[2],-v[1]}}
func build(source []byte,profile string)(typed.Packet,Ledger,error){
 if profile!="forward"&&profile!="outward"{return typed.Packet{},Ledger{},errors.New("PROFILE")}
 a,e:=solvera.Run(source);if e!=nil{return typed.Packet{},Ledger{},e}
 var fixtures solvera.Fixtures
 if e=json.Unmarshal(source,&fixtures);e!=nil{return typed.Packet{},Ledger{},e}
 identity:=Quaternion{0,0,0,1}
 actors:=[]typed.Actor{};maxFK:=0.;maxBasis:=0.;ids:=[]string{}
 for i,name:=range []string{"CobaltOriginal","MarigoldOriginal"}{
  c:=fixtures.Cases[i]
  result,e:=solvera.Solve(c);if e!=nil||!result.Reached{return typed.Packet{},Ledger{},errors.New("SELECTED_SOURCE_CASE_UNREACHABLE")}
  ids=append(ids,c.ID)
  root:=Vec(c.Start);knee:=Vec(result.Knee);end:=Vec(result.End)
  upper:=minus(knee,root);lower:=minus(end,knee)
  worldUpper,e:=between(Vec{0,-1,0},upper);if e!=nil{return typed.Packet{},Ledger{},e}
  worldLower,e:=between(Vec{0,-1,0},lower);if e!=nil{return typed.Packet{},Ledger{},e}
  // Lower WORLD quaternion is transformed into child-local by inverse parent.
  localLower,e:=normalized(multiply(inverse(worldUpper),worldLower));if e!=nil{return typed.Packet{},Ledger{},e}
  // Nonzero synthetic actor separation is explicit staged derivation, not a
  // sampled human scene or inferred source tracking.
  lateral:=1.65
  if i==0{lateral= -1.65}
  frames:=[]typed.Frame{}
  for _,frame:=range []int{0,12,24}{
   shift:=Vec{lateral+float64(frame)/120,0,0}
   measured:=[]Vec{root,knee,end}
   for _,v:=range measured {
    roundtrip:=toGLTF(toBlender(v))
    err:=norm(minus(roundtrip,v));if err>maxBasis{maxBasis=err}
    if err>1e-12{return typed.Packet{},Ledger{},errors.New("SYNTHETIC_BASIS_ROUNDTRIP")}
   }
   predictedUpper:=rotate(worldUpper,Vec{0,-c.Upper,0})
   predictedLower:=rotate(multiply(worldUpper,localLower),Vec{0,-c.Lower,0})
   residual:=math.Max(norm(minus(predictedUpper,upper)),norm(minus(predictedLower,lower)))
   if residual>maxFK{maxFK=residual}
   if residual>1e-8{return typed.Packet{},Ledger{},errors.New("PARENT_LOCAL_QUAT_FK")}
   frames=append(frames,typed.Frame{Index:ptr(frame),TimeNum:ptr(frame),TimeDen:ptr(12),
    Root:asV(plus(root,shift)),
    Local:map[string]typed.Q{"root":asQ(identity),"hip":asQ(worldUpper),"knee":asQ(localLower),"ankle":asQ(identity)},
    Foot:typed.Contact{State:"unknown"}})
  }
  actors=append(actors,typed.Actor{ID:name,Profile:profile,Bones:[]typed.Bone{
   {ID:"root",Parent:"",Rest:asV(Vec{})},
   {ID:"hip",Parent:"root",Rest:asV(Vec{})},
   {ID:"knee",Parent:"hip",Rest:asV(Vec{0,-c.Upper,0})},
   {ID:"ankle",Parent:"knee",Rest:asV(Vec{0,-c.Lower,0})},
  },Frames:frames})
 }
 p:=typed.Packet{Schema:"scp.walk_motion_3d.v2",Rights:"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
  OriginCommit:originA,Basis:"GLTF_RH_Y_UP_UNCALIBRATED",
  BasisConversion:"BLENDER_Z_UP_TO_GLTF_Y_UP_EXPLICIT",Units:"UNCALIBRATED_SOURCE_SCENE",
  FPSNum:ptr(12),FPSDen:ptr(1),Actors:actors}
 if err:=typed.Validate(p);err!=nil{return typed.Packet{},Ledger{},fmt.Errorf("ORIGINAL_W16A_VALIDATOR:%w",err)}
 raw,e:=json.Marshal(p);if e!=nil{return typed.Packet{},Ledger{},e}
 if _,e:=typed.Decode(raw);e!=nil{return typed.Packet{},Ledger{},fmt.Errorf("ORIGINAL_W16A_DECODER:%w",e)}
 hash:=sha256.Sum256(raw)
 ledger:=Ledger{Schema:"scp.walk_w16b2_admission_receipt.v1",Status:"PASS_STRUCTURAL_AND_ANALYTIC_SYNTHETIC_DERIVATION_ONLY",
  SourceFixtureSHA256:a.SourceSHA,DerivedPacketSHA256:fmt.Sprintf("%x",hash),
  OriginalW13ACommit:originA,StructuralW16ACommit:originW16,
  SpatialCaseIDs:ids,MaxAnalyticFKError:maxFK,MaxBasisRoundtripError:maxBasis,
  SyntheticTimeOnly:true,NativeSourceTimeAdmitted:false,ActualWeightedSkinAdmitted:false,
  SourceAndRightsPolicy:"W13_A_ORIGINAL_PROCEDURAL_TO_NEW_SYNTHETIC_DERIVATION_REQUIRES_INDEPENDENT_ORIGIN_AND_REAL_GAIT_ADMISSION"}
 return p,ledger,nil
}
func main(){
 if len(os.Args)!=5{fmt.Fprintln(os.Stderr,"usage: w16b2 <forward|outward> pinned-w13-fixture.json derived-packet.json receipt.json");os.Exit(2)}
 raw,e:=os.ReadFile(os.Args[2]);if e!=nil{panic(e)}
 p,r,e:=build(raw,os.Args[1]);if e!=nil{panic(e)}
 data,e:=json.MarshalIndent(p,"","  ");if e!=nil{panic(e)}
 if e=os.WriteFile(os.Args[3],append(data,10),0644);e!=nil{panic(e)}
 data,e=json.MarshalIndent(r,"","  ");if e!=nil{panic(e)}
 if e=os.WriteFile(os.Args[4],append(data,10),0644);e!=nil{panic(e)}
 fmt.Println("W16B2_STRUCTURE_FK_SYNTHETIC_ONLY_PASS",r.MaxAnalyticFKError,r.DerivedPacketSHA256)
}
