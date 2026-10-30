package typed

// W16 source-only motion.v2 admission. No human, private assets, or realism claims.
// A 3D motion contract is distinct from a verified animation/retarget solve.
import (
 "bytes"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "math"
)

const rights="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
const schema="scp.walk_motion_3d.v2"
const basis="GLTF_RH_Y_UP_UNCALIBRATED"
const conversion="BLENDER_Z_UP_TO_GLTF_Y_UP_EXPLICIT"
const origin="dcc47118a508379047d9707efe5b2039a86f3531" // source candidate, not approved merge

type V [3]float64
type Q [4]float64 // glTF XYZW; Blender native uses WXYZ
type Bone struct { ID string `json:"id"`; Parent string `json:"parent"`; Rest V `json:"rest"` }
type Contact struct { State string `json:"state"`; Anchor *V `json:"world_anchor,omitempty"` }
type Frame struct {
 Index *int `json:"frame"`
 TimeNum *int `json:"time_num"`
 TimeDen *int `json:"time_den"`
 Root V `json:"root_xyz"`
 Local map[string]Q `json:"local_quat_xyzw"`
 Foot Contact `json:"foot_contact"`
}
type Actor struct {
 ID string `json:"id"`
 Profile string `json:"profile"`
 Bones []Bone `json:"bones"`
 Frames []Frame `json:"frames"`
}
type Packet struct {
 Schema string `json:"schema"`
 Rights string `json:"source_rights"`
 OriginCommit string `json:"origin_commit_sha"`
 Basis string `json:"coordinate_basis"`
 BasisConversion string `json:"basis_conversion"`
 Units string `json:"units"`
 FPSNum *int `json:"fps_num"`
 FPSDen *int `json:"fps_den"`
 Actors []Actor `json:"actors"`
}
type Receipt struct {
 Schema string `json:"schema"`
 Status string `json:"status"`
 SourceSHA256 string `json:"source_sha256"`
 SourceRights string `json:"source_rights"`
 ActorCount int `json:"actor_count"`
 FrameCount int `json:"frame_count"`
 Scope string `json:"scope"`
}
func validV(v V) bool { for _,x:=range v {if math.IsNaN(x)||math.IsInf(x,0) {return false}};return true }
func validQ(q Q)bool{
 sum:=0.0
 for _,x:=range q { if math.IsNaN(x)||math.IsInf(x,0) {return false};sum+=x*x }
 return math.Abs(sum-1)<1e-6
}
func distance(a,b V)float64 {
 return math.Hypot(math.Hypot(a[0]-b[0],a[1]-b[1]),a[2]-b[2])
}
func fail(s string)error{return errors.New(s)}
func Validate(p Packet)error {
 if p.Schema!=schema||p.Rights!=rights||p.Basis!=basis||
 p.BasisConversion!=conversion||p.Units!="UNCALIBRATED_SOURCE_SCENE" {return fail("SCHEMA_RIGHTS_UNITS_OR_BASIS")}
 if len(p.OriginCommit)!=40 {return fail("ORIGIN_COMMIT_MISSING")}
 if _,e:=hex.DecodeString(p.OriginCommit);e!=nil{return fail("ORIGIN_COMMIT_INVALID")}
 if p.FPSNum==nil||p.FPSDen==nil||*p.FPSNum!=12||*p.FPSDen!=1{return fail("CLOCK_UNADMITTED")}
 if len(p.Actors)!=2{return fail("ACTOR_COUNT")}
 ids:=map[string]bool{}
 for _,a:=range p.Actors {
  if a.ID==""||ids[a.ID]||!(a.Profile=="forward"||a.Profile=="outward"){return fail("ACTOR_ID_OR_PROFILE")}
  ids[a.ID]=true
  if len(a.Bones)!=4||len(a.Frames)!=3{return fail("BONE_OR_FRAME_COUNT")}
  parent:=map[string]string{}
  for _,b:=range a.Bones {
   if b.ID==""||!validV(b.Rest) {return fail("BONE_MISSING_OR_NONFINITE")}
   if _,ok:=parent[b.ID];ok{return fail("BONE_DUPLICATE")}
   parent[b.ID]=b.Parent
  }
  if parent["root"]!="" {return fail("ROOT_PARENT")}
  for _,id:=range []string{"root","hip","knee","ankle"} {if _,ok:=parent[id];!ok{return fail("BONE_REQUIRED")}}
  for id:=range parent {
   seen:=map[string]bool{}
   for cur:=id;cur!="";cur=parent[cur] {
    if seen[cur] {return fail("PARENT_CYCLE")}
    seen[cur]=true
    if _,ok:=parent[cur];!ok {return fail("PARENT_UNKNOWN")}
   }
  }
  var prior *V
  previous:=-1
  for _,f:=range a.Frames{
   if f.Index==nil||f.TimeNum==nil||f.TimeDen==nil{return fail("CLOCK_FIELD_MISSING")}
   if *f.Index<0||*f.Index<=previous||*f.TimeNum!=*f.Index||*f.TimeDen!=12{return fail("CLOCK_NONCANONICAL")}
   previous=*f.Index
   if !validV(f.Root)||len(f.Local)!=len(parent){return fail("ROOT_OR_ROTATIONS")}
   for id:=range parent {q,ok:=f.Local[id];if !ok||!validQ(q){return fail("MISSING_OR_BAD_QUAT_XYZW")}}
   if f.Foot.State=="stance" {
    if f.Foot.Anchor==nil||!validV(*f.Foot.Anchor){return fail("STANCE_WITHOUT_ANCHOR")}
    if prior!=nil&&distance(*prior,*f.Foot.Anchor)>1e-6{return fail("PLANTED_FOOT_SLIP")}
    v:=*f.Foot.Anchor;prior=&v
   } else if f.Foot.State=="swing"||f.Foot.State=="unknown" {
    if f.Foot.Anchor!=nil{return fail("UNOBSERVED_CONTACT_ANCHOR")}
    prior=nil
   } else {return fail("CONTACT_STATE_INVALID")}
  }
  if a.Frames[0].Index==nil||*a.Frames[0].Index!=0{return fail("T0_NOT_ZERO")}
 }
 if !ids["CobaltOriginal"]||!ids["MarigoldOriginal"]{return fail("ORIGINAL_ACTOR_IDS")}
 return nil
}
func Decode(b []byte)(Packet,error){
 var p Packet
 dec:=json.NewDecoder(bytes.NewReader(b));dec.DisallowUnknownFields()
 if e:=dec.Decode(&p);e!=nil{return Packet{},e}
 var trailing interface{}
 if e:=dec.Decode(&trailing);e!=io.EOF{return Packet{},fail("TRAILING_OR_MALFORMED_JSON")}
 return p,Validate(p)
}
func ptr(x int)*int{return &x}
func sample(profile string)Packet{
 q:=Q{0,0,0,1}
 actor:=func(id string,side float64)Actor{
  frames:=[]Frame{}
  for n,frame:=range []int{0,12,24} {
   contact:=Contact{State:"stance",Anchor:&V{side,0,0}}
   if n==2 {contact=Contact{State:"swing"}}
   frames=append(frames,Frame{Index:ptr(frame),TimeNum:ptr(frame),TimeDen:ptr(12),
   Root:V{side*(1.0-float64(n)*.25),0,0},Local:map[string]Q{"root":q,"hip":q,"knee":q,"ankle":q},Foot:contact})
  }
  return Actor{ID:id,Profile:profile,Bones:[]Bone{
   {"root","",V{0,0,0}},{"hip","root",V{0,1,0}},
   {"knee","hip",V{0,-.6,0}},{"ankle","knee",V{0,-.6,0}},
  },Frames:frames}
 }
 return Packet{Schema:schema,Rights:rights,OriginCommit:origin,Basis:basis,BasisConversion:conversion,
 Units:"UNCALIBRATED_SOURCE_SCENE",FPSNum:ptr(12),FPSDen:ptr(1),
 Actors:[]Actor{actor("CobaltOriginal",-1.0),actor("MarigoldOriginal",1.0)}}
}