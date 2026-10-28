package main

// W07 original public-only two-character pose/contact transfer.
// This is 2D source-space inverse kinematics, not real anatomy or skinned mesh.
import (
 "crypto/sha256"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "math"
 "os"
)
const rights="ORIGINAL_PROGRAMMATIC_PROCEDURAL_ONLY"
const schema="scp.walk_motion.v1"
const outschema="scp.walk_transfer_synthetic.v1"
var IDs=[]string{"cobalt-automaton","marigold-explorer"}
type V [2]float64
type Pose struct {
 Root float64 `json:"root_x"`
 Facing int `json:"facing"`
 Joints map[string]V `json:"joints"`
 Contact map[string]bool `json:"contact"`
}
type Frame struct {
 Index int `json:"index"`
 Timestamp int `json:"timestamp_ms"`
 Actors map[string]Pose `json:"actors"`
}
type Source struct {
 Schema string `json:"schema"`
 Rights string `json:"source_rights"`
 FPS int `json:"fps"`
 FramesCount int `json:"frames_count"`
 Actors []struct{ ID string `json:"id"` } `json:"actors"`
 Frames []Frame `json:"frames"`
}
type Leg struct { Thigh float64 `json:"thigh"`; Shin float64 `json:"shin"` }
type Transfer struct {
 Schema string `json:"schema"`
 Status string `json:"status"`
 SourceSchema string `json:"source_schema"`
 SourceRights string `json:"source_rights"`
 SourceSHA string `json:"source_sha256"`
 Target string `json:"target_profile"`
 TargetLegs map[string]Leg `json:"target_legs"`
 Frames []Frame `json:"frames"`
 MaxSlip float64 `json:"max_planted_foot_slip"`
 MaxResidual float64 `json:"max_ik_length_residual"`
 MinGap float64 `json:"min_root_gap"`
 Scope string `json:"scope"`
}
func finite(n float64)bool{return !math.IsNaN(n)&&!math.IsInf(n,0)}
func distance(a,b V)float64{return math.Hypot(a[0]-b[0],a[1]-b[1])}
func knee(hip,ankle V, facing int, l Leg)(V,error){
 if !finite(hip[0])||!finite(hip[1])||!finite(ankle[0])||!finite(ankle[1])||!finite(l.Thigh)||!finite(l.Shin)||l.Thigh<=0||l.Shin<=0||(facing!=1&&facing!= -1){return V{},errors.New("INVALID_IK_INPUT")}
 d:=distance(hip,ankle)
 if d<=math.Abs(l.Thigh-l.Shin)+1e-8||d>=l.Thigh+l.Shin-1e-8{return V{},errors.New("IK_UNREACHABLE")}
 along:=(l.Thigh*l.Thigh-l.Shin*l.Shin+d*d)/(2*d)
 perp:=math.Sqrt(math.Max(0,l.Thigh*l.Thigh-along*along))
 ux:=(ankle[0]-hip[0])/d; uy:=(ankle[1]-hip[1])/d
 x:=V{hip[0]+along*ux-float64(facing)*perp*uy,hip[1]+along*uy+float64(facing)*perp*ux}
 return x,nil
}
func legs(profile string)(map[string]Leg,error){
 switch profile{
 case "different-proportions":return map[string]Leg{IDs[0]:{.67,.55},IDs[1]:{.55,.69}},nil
 case "compact-and-tall":return map[string]Leg{IDs[0]:{.59,.55},IDs[1]:{.72,.61}},nil
 }
 return nil,errors.New("UNADMITTED_TARGET_PROFILE")
}
func Retarget(s Source, sha, profile string)(Transfer,error){
 spec,err:=legs(profile);if err!=nil{return Transfer{},err}
 if s.Schema!=schema||s.Rights!=rights||s.FPS!=12||s.FramesCount!=72||len(s.Frames)!=72||len(s.Actors)!=2||len(sha)!=64{return Transfer{},errors.New("RIGHTS_SCHEMA_OR_CLOCK")}
 if s.Actors[0].ID!=IDs[0]||s.Actors[1].ID!=IDs[1]{return Transfer{},errors.New("ACTOR_IDENTITY")}
 t:=Transfer{Schema:outschema,SourceSchema:s.Schema,SourceRights:s.Rights,SourceSHA:sha,Target:profile,TargetLegs:spec,MinGap:math.Inf(1),Scope:"ORIGINAL_SYNTHETIC_2D_CONTACT_ONLY_NOT_PRIVATE_REAL_PERSON_NOT_NATIVE_SKIN"}
 initial:=map[string]float64{};previous:=map[string]Pose{}
 for i,f:=range s.Frames{
  if f.Index!=i||f.Timestamp!=int(math.Round(float64(i)*1000/12))||len(f.Actors)!=2{return Transfer{},errors.New("FRAME_INDEX_OR_TIMESTAMP")}
  row:=Frame{Index:i,Timestamp:f.Timestamp,Actors:map[string]Pose{}}
  for idx,id:=range IDs{
   p,ok:=f.Actors[id];direction:=1;if idx==1{direction= -1}
   if !ok||p.Facing!=direction||len(p.Contact)!=2||len(p.Joints)<16||!finite(p.Root){return Transfer{},errors.New("SOURCE_ACTOR_MISSING_OR_FORGED")}
   if i==0{initial[id]=p.Root}
   joints:=make(map[string]V,len(p.Joints))
   for k,v:=range p.Joints{if !finite(v[0])||!finite(v[1]){return Transfer{},errors.New("NONFINITE_JOINT")};joints[k]=v}
   for _,side:=range []string{"left","right"}{
    a,aok:=joints["ankle_"+side];h,hok:=joints["hip_"+side]
    if !aok||!hok||!finite(a[1])||a[1]<.1099999||a[1]>1{return Transfer{},errors.New("INVALID_SOURCE_ANKLE_OR_HIP")}
    k,e:=knee(h,a,p.Facing,spec[id]);if e!=nil{return Transfer{},fmt.Errorf("frame=%d actor=%s side=%s: %w",i,id,side,e)}
    joints["knee_"+side]=k
    t.MaxResidual=math.Max(t.MaxResidual,math.Abs(distance(h,k)-spec[id].Thigh))
    t.MaxResidual=math.Max(t.MaxResidual,math.Abs(distance(k,a)-spec[id].Shin))
    if i>0&&p.Contact[side]&&previous[id].Contact[side]{
      slip:=distance(a,previous[id].Joints["ankle_"+side])
      t.MaxSlip=math.Max(t.MaxSlip,slip)
      if slip>1e-7{return Transfer{},errors.New("PLANTED_FOOT_SLIP")}
    }
   }
   row.Actors[id]=Pose{Root:p.Root,Facing:p.Facing,Joints:joints,Contact:p.Contact}
  }
  gap:=row.Actors[IDs[1]].Root-row.Actors[IDs[0]].Root
  t.MinGap=math.Min(t.MinGap,gap)
  if gap<1.5{return Transfer{},errors.New("ACTOR_COLLISION")}
  for _,id:=range IDs{previous[id]=row.Actors[id]}
  t.Frames=append(t.Frames,row)
 }
 for i,id:=range IDs{d:=1.0;if i==1{d= -1};if d*(t.Frames[71].Actors[id].Root-initial[id])<1.7{return Transfer{},errors.New("NO_APPROACH")}}
 if t.MaxResidual>1e-8||t.MaxSlip>1e-7{return Transfer{},errors.New("SOURCE_CONTACT_OR_SEGMENT_RESIDUAL")}
 t.Status="PASS_ORIGINAL_SYNTHETIC_CONTACT_PRESERVING_RETARGET"
 return t,nil
}
func main(){
 source:=flag.String("source","","canonical W06 source JSON")
 target:=flag.String("target","different-proportions","allowed original target profile")
 out:=flag.String("out","","output machine JSON")
 flag.Parse()
 if *source==""||*out==""{panic("source/out required")}
 b,err:=os.ReadFile(*source);if err!=nil{panic(err)}
 var s Source;if err=json.Unmarshal(b,&s);err!=nil{panic(err)}
 hash:=sha256.Sum256(b)
 t,err:=Retarget(s,fmt.Sprintf("%x",hash),*target);if err!=nil{panic(err)}
 body,err:=json.MarshalIndent(t,"","  ");if err!=nil{panic(err)}
 if err=os.WriteFile(*out,append(body,10),0644);err!=nil{panic(err)}
 fmt.Printf("W07_CANONICAL_W06_TRANSFER_PASS target=%s frames=%d slip=%g residual=%g min_gap=%g\n",*target,len(t.Frames),t.MaxSlip,t.MaxResidual,t.MinGap)
}
