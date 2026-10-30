package main
// W4j-A2: Fail-closed synthetic source-owned sole event to 48k sample clock.
// Actual W16-D3 geometric mesh is NOT a foot; no morphology, contact or force inferred.
import ("encoding/json";"errors";"fmt";"math";"os")
const rights="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC"
const hz=48000
const groundTolerance=1e-4
const plantedSlip=1e-3
type XYZ [3]float64
type Frame struct {Index int `json:"index"`; Heel XYZ `json:"heel"`; Toe XYZ `json:"toe"`}
type Trace struct {
 Schema string `json:"schema"`
 Rights string `json:"rights"`
 Basis string `json:"basis"`
 FootSource string `json:"foot_source"`
 FootID string `json:"foot_id"`
 ClockFPS int `json:"clock_fps"`
 AudioHz int `json:"audio_hz"`
 NativeMinMeshGroundClearance float64 `json:"native_min_mesh_ground_clearance"`
 Frames []Frame `json:"frames"`
}
type Event struct {FootID string `json:"foot_id"`; Frame int `json:"frame"`; Sample int `json:"sample"`; Source string `json:"source"`}
type Receipt struct {Schema string `json:"schema"`; Status string `json:"status"`; Reason string `json:"reason"`; Profile string `json:"profile"`; Events []Event `json:"events"`; FrozenGroundTolerance float64 `json:"frozen_ground_tolerance"`; FrozenStanceSlip float64 `json:"frozen_stance_slip"`; Source Trace `json:"source"`}
func dist(a,b XYZ)float64{return math.Sqrt((a[0]-b[0])*(a[0]-b[0])+(a[1]-b[1])*(a[1]-b[1])+(a[2]-b[2])*(a[2]-b[2]))}
func valid(v XYZ)bool{for _,x:=range v{if math.IsNaN(x)||math.IsInf(x,0){return false}};return true}
func classify(t Trace)(Receipt,error){
 r:=Receipt{Schema:"scp.w4j_a2_contact_foley.v1",Status:"ABSTAIN",Reason:"UNVERIFIED_ANATOMICAL_SOLE",Profile:t.FootSource,Events:[]Event{},FrozenGroundTolerance:groundTolerance,FrozenStanceSlip:plantedSlip,Source:t}
 if t.Schema!="scp.w4j_original_synthetic_trace.v1"||t.Rights!=rights||t.Basis!="RH_Z_UP_SOURCE_SCENE"||t.ClockFPS!=12||t.AudioHz!=hz||t.FootID==""{return r,errors.New("RIGHTS_CLOCK_BASIS_SOURCE_INVALID")}
 if math.IsNaN(t.NativeMinMeshGroundClearance)||math.IsInf(t.NativeMinMeshGroundClearance,0)||t.NativeMinMeshGroundClearance<0 {return r,errors.New("INVALID_NATIVE_GROUND_WITNESS")}
 if t.FootSource!="SOURCE_DEFINED_ARTIFICIAL_SOLE"&&t.FootSource!="NATIVE_UNLABELED_MESH" {return r,errors.New("INVALID_FOOT_OWNERSHIP")}
 if t.FootSource=="NATIVE_UNLABELED_MESH" {
  // W16-D3 actually observed a non-grounded mesh clearance, with no heel/toe labels.
  if len(t.Frames)!=0||t.NativeMinMeshGroundClearance<groundTolerance{return r,errors.New("NATIVE_WITNESS_WAS_INVENTED")}
  return r,nil
 }
 if len(t.Frames)<3||len(t.Frames)>1000||t.NativeMinMeshGroundClearance!=0{return r,errors.New("SYNTHETIC_SOURCE_FOOT_TRACE")}
 touched:=false
 var previous Frame
 for i,f:=range t.Frames{
  if f.Index!=i||!valid(f.Heel)||!valid(f.Toe){return r,errors.New("SOURCE_FRAME_NONFINITE_OR_CLOCK")}
  if f.Heel[2] < -groundTolerance||f.Toe[2] < -groundTolerance{return r,errors.New("PENETRATION")}
  now:=math.Abs(f.Heel[2])<=groundTolerance&&math.Abs(f.Toe[2])<=groundTolerance
  if now&&touched {
   if dist(f.Heel,previous.Heel)>plantedSlip||dist(f.Toe,previous.Toe)>plantedSlip{return r,errors.New("PLANTED_FOOT_SKATING")}
  }
  if now&&!touched{r.Events=append(r.Events,Event{FootID:t.FootID,Frame:f.Index,Sample:f.Index*(hz/12),Source:"EXPLICIT_SYNTHETIC_HEEL_TOE_GEOMETRY"})}
  touched=now;previous=f
 }
 if len(r.Events)==0{r.Reason="NO_SYNTHETIC_CONTACT";return r,nil}
 r.Status="PASS_SYNTHETIC_CONTACT_EVENTS_ONLY";r.Reason="ARTIFICIAL_SOLE_NOT_ANATOMICAL";return r,nil
}
func fixtures(profile string)Trace{
 t:=Trace{Schema:"scp.w4j_original_synthetic_trace.v1",Rights:rights,Basis:"RH_Z_UP_SOURCE_SCENE",FootID:"OriginalToyLeft",ClockFPS:12,AudioHz:hz}
 switch profile{
 case "toy":
  t.FootSource="SOURCE_DEFINED_ARTIFICIAL_SOLE"
  t.Frames=[]Frame{
   {Index:0,Heel:XYZ{0,0,.2},Toe:XYZ{0,.2,.15}},
   {Index:1,Heel:XYZ{0,0,0},Toe:XYZ{0,.2,0}},
   {Index:2,Heel:XYZ{0,0,0},Toe:XYZ{0,.2,0}},
   {Index:3,Heel:XYZ{0,0,.15},Toe:XYZ{0,.2,.16}},
   {Index:4,Heel:XYZ{0,0,0},Toe:XYZ{0,.2,0}},
  }
 case "native":
  t.FootSource="NATIVE_UNLABELED_MESH";t.NativeMinMeshGroundClearance=.2700000107;t.Frames=[]Frame{}
 }
 return t
}
func main(){
 if len(os.Args)!=3||os.Args[1]!="toy"&&os.Args[1]!="native"{panic("usage: w4j toy|native output.json")}
 profile:=os.Args[1];r,e:=classify(fixtures(profile));if e!=nil{panic(e)}
 b,e:=json.MarshalIndent(r,"","  ");if e!=nil{panic(e)}
 if e=os.WriteFile(os.Args[2],append(b,'
'),0644);e!=nil{panic(e)}
 fmt.Println("W4J_A2_CONTACT_TO_SAMPLE",profile,r.Status,len(r.Events))
}
