// W8-A source-behavior invariants for original-only W7A; never a human ROM oracle.
package main

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "math"
 "os"
)

const rights = "ORIGINAL_SELF_AUTHORED_SYNTHETIC"
const schema = "scp.walk_w7a_original_approach.v1"
type Leg struct {
 ID string `json:"id"`
 State string `json:"state"`
 Hip []float64 `json:"hip"`
 Knee []float64 `json:"knee"`
 Ankle []float64 `json:"ankle"`
 Heel []float64 `json:"heel"`
 Toe []float64 `json:"toe"`
 Anchor []float64 `json:"anchor"`
}
type Frame struct {
 Index int `json:"index"`
 TimeNum int `json:"time_num"`
 TimeDen int `json:"time_den"`
 RootX float64 `json:"root_x"`
 Legs []Leg `json:"legs"`
}
type Actor struct { ID string `json:"id"`; Frames []Frame `json:"frames"` }
type Source struct {
 Schema string `json:"schema"`
 Rights string `json:"rights"`
 Profile string `json:"profile"`
 Scenario string `json:"scenario"`
 FPSNum int `json:"fps_num"`
 FPSDen int `json:"fps_den"`
 Actors []Actor `json:"actors"`
}
type Finding struct {
 Code string `json:"code"`
 Status string `json:"status"`
 Actor string `json:"actor,omitempty"`
 Leg string `json:"leg,omitempty"`
 FrameStart int `json:"frame_start"`
 FrameEnd int `json:"frame_end"`
}
type Receipt struct {
 Schema string `json:"schema"`
 SourceSHA string `json:"source_sha256"`
 Profile string `json:"profile"`
 SourceIntegrity string `json:"source_integrity"`
 SourceBehavior string `json:"source_behavior"`
 HumanGait string `json:"human_gait"`
 AnimalGait string `json:"animal_gait"`
 MechanicalMotion string `json:"mechanical_motion"`
 PhysicalForce string `json:"physical_force"`
 RenderedBehavior string `json:"rendered_behavior"`
 Findings []Finding `json:"findings"`
}
func vec3(v []float64) bool {
 if len(v)!=3 { return false }
 for _,x:=range v { if math.IsNaN(x)||math.IsInf(x,0) { return false } }
 return true
}
func dist(a,b []float64) float64 { var s float64;for i:=0;i<3;i++ { d:=a[i]-b[i];s+=d*d };return math.Sqrt(s) }
func Evaluate(s Source, digest string) Receipt {
 r:=Receipt{Schema:"scp.visualqa_w8a.source_behavior.v1",SourceSHA:digest,Profile:s.Profile,
  SourceIntegrity:"PASS_SOURCE_CONTRACT_KINEMATIC_ONLY",
  SourceBehavior:"ABSTAIN_INSUFFICIENT_ANATOMICAL_INPUT",
  HumanGait:"ABSTAIN_NO_ANATOMICAL_JCS_FULLBODY_OR_NORMATIVE_MODEL",
  AnimalGait:"ABSTAIN_ENTITY_NOT_ANIMAL",MechanicalMotion:"ABSTAIN_NO_ACTUATOR_LIMITS",
  PhysicalForce:"UNKNOWN_UNMEASURED",RenderedBehavior:"NOT_RUN_CLEAN_VIDEO_SEPARATE",
  Findings:[]Finding{}}
 fail:=func(code,actor,leg string,at int) {
  r.SourceIntegrity="FAIL";r.SourceBehavior="FAIL_SOURCE_KINEMATIC_INVARIANT"
  r.Findings=append(r.Findings,Finding{Code:code,Status:"FAIL",Actor:actor,Leg:leg,FrameStart:at,FrameEnd:at})
 }
 if s.Schema!=schema||s.Rights!=rights||s.Scenario!="ORIGINAL_2ACTOR_WORLD_X_APPROACH_NOT_HUMAN_GAIT"||s.FPSNum!=12||s.FPSDen!=1||len(s.Actors)!=2||(s.Profile!="forward"&&s.Profile!="outward") {
  fail("W8_SOURCE_ID_RIGHTS_CLOCK","","",-1);return r
 }
 seen:=map[string]bool{}
 for ai,a:=range s.Actors {
  if a.ID==""||seen[a.ID]||len(a.Frames)!=24 {fail("W8_ACTOR_ID_OR_FRAME_COUNT",a.ID,"",-1);continue}
  seen[a.ID]=true
  for i,f:=range a.Frames {
   if f.Index!=i||f.TimeNum!=i||f.TimeDen!=12||math.IsNaN(f.RootX)||math.IsInf(f.RootX,0) {fail("W8_CLOCK_OR_ROOT_NONFINITE",a.ID,"",i);continue}
   if len(f.Legs)!=2 {fail("W8_INCOMPLETE_LEG_SET",a.ID,"",i);continue}
   for li,leg:=range f.Legs {
    want:="Left";if li==1 {want="Right"}
    if leg.ID!=want {fail("W8_SWAPPED_LEFT_RIGHT",a.ID,leg.ID,i);continue}
    if !vec3(leg.Hip)||!vec3(leg.Knee)||!vec3(leg.Ankle)||!vec3(leg.Heel)||!vec3(leg.Toe) {fail("W8_NONFINITE_OR_MISSING_GEOMETRY",a.ID,leg.ID,i);continue}
    if leg.Ankle[2]<-0.0001||leg.Heel[2]<-0.0001||leg.Toe[2]<-0.0001 {fail("W8_GROUND_PENETRATION",a.ID,leg.ID,i)}
    if leg.State=="stance" {
     if !vec3(leg.Anchor) {fail("W8_MISSING_STANCE_ANCHOR",a.ID,leg.ID,i);continue}
     if dist(leg.Ankle,leg.Anchor)>.001||math.Abs(leg.Heel[2])>.0001||math.Abs(leg.Toe[2])>.0001 {
      fail("W8_STANCE_SLIP_OR_FALSE_CONTACT",a.ID,leg.ID,i)
     }
     if i>0&&a.Frames[i-1].Legs[li].State=="stance"&&vec3(a.Frames[i-1].Legs[li].Heel)&&dist(leg.Heel,a.Frames[i-1].Legs[li].Heel)>.001 {
      fail("W8_PLANTED_HEEL_SUDDEN_MOVE",a.ID,leg.ID,i)
     }
    } else if leg.State!="swing" {fail("W8_UNRECOGNIZED_CONTACT_STATE",a.ID,leg.ID,i)}
   }
   if i>0&&i<len(a.Frames) {
    prev:=a.Frames[i-1].RootX
    if (ai==0&&f.RootX<prev-1e-8)||(ai==1&&f.RootX>prev+1e-8) {
     fail("W8_REVERSED_OR_DISCONTINUOUS_ACTION_DIRECTION",a.ID,"",i)
    }
   }
  }
 }
 if len(s.Actors)==2&&len(s.Actors[0].Frames)==24&&len(s.Actors[1].Frames)==24 {
  for i:=0;i<24;i++ {
   x0:=s.Actors[0].Frames[i].RootX;x1:=s.Actors[1].Frames[i].RootX
   if x0>=x1 {fail("W8_ACTOR_ROOT_ORDER_CROSSED","","",i)}
  }
 }
 if r.SourceIntegrity!="FAIL" {
  r.Findings=append(r.Findings,Finding{Code:"W8_NO_RIGGED_TORSO_OR_ARMS",Status:"ABSTAIN",FrameStart:0,FrameEnd:23})
  r.Findings=append(r.Findings,Finding{Code:"W8_NO_APPROVED_HUMAN_JCS_ROM_OR_KNEE_SIGN",Status:"ABSTAIN",FrameStart:0,FrameEnd:23})
  r.Findings=append(r.Findings,Finding{Code:"W8_NO_MEASURED_FORCE_OR_CONTACT_DYNAMICS",Status:"UNKNOWN",FrameStart:0,FrameEnd:23})
 }
 return r
}
func main() {
 if len(os.Args)!=3 {fmt.Fprintln(os.Stderr,"usage: w8a SOURCE.json RECEIPT.json");os.Exit(2)}
 raw,e:=os.ReadFile(os.Args[1]);if e!=nil {panic(e)}
 var s Source
 if e=json.Unmarshal(raw,&s);e!=nil {panic(e)}
 digest:=sha256.Sum256(raw)
 r:=Evaluate(s,hex.EncodeToString(digest[:]))
 out,e:=json.MarshalIndent(r,"","  ");if e!=nil {panic(e)}
 if e=os.WriteFile(os.Args[2],append(out,'
'),0644);e!=nil {panic(e)}
 fmt.Println(r.SourceIntegrity,r.SourceBehavior,r.HumanGait)
 if r.SourceIntegrity=="FAIL" {os.Exit(1)}
}
