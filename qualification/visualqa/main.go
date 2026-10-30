// Autonomous source-original independent 3D knee-pole geometry guard.
// PASS means only declared rest-basis knee direction + lengths are satisfied;
// it DOES NOT mean anatomical realism, contact, video-to-rig parity or identity.
package main

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "flag"
 "fmt"
 "math"
 "os"
)

type V [3]float64
func (v V) sub(w V) V { return V{v[0]-w[0],v[1]-w[1],v[2]-w[2]} }
func (v V) dot(w V) float64 { return v[0]*w[0]+v[1]*w[1]+v[2]*w[2] }
func (v V) scale(a float64) V { return V{v[0]*a,v[1]*a,v[2]*a} }
func (v V) norm() float64 { return math.Sqrt(v.dot(v)) }
func (v V) finite() bool { for _,x:=range v { if math.IsNaN(x)||math.IsInf(x,0) {return false} };return true }
type Spec struct { Actor string `json:"actor"`; Leg string `json:"leg"`; Pole V `json:"pole"`; Upper float64 `json:"upper"`; Lower float64 `json:"lower"` }
type Pose struct { Actor string `json:"actor"`; Leg string `json:"leg"`; Hip V `json:"hip"`; Knee V `json:"knee"`; Ankle V `json:"ankle"` }
type Frame struct { Tick int64 `json:"tick"`; Poses []Pose `json:"poses"` }
type Input struct { Schema string `json:"schema"`; Rights string `json:"rights"`; SourceSHA256 string `json:"source_sha256"`; Legs []Spec `json:"legs"`; Frames []Frame `json:"frames"` }
type Finding struct { Frame int64 `json:"frame"`; Actor string `json:"actor"`; Leg string `json:"leg"`; Severity string `json:"severity"`; Reason string `json:"reason"`; SignedPoleCos float64 `json:"signed_pole_cos,omitempty"`; FlexDegrees float64 `json:"flex_degrees,omitempty"` }
type Result struct { Schema string `json:"schema"`; Status string `json:"status"`; SourceSHA256 string `json:"source_sha256"`; VerifiedSourceBytes bool `json:"verified_source_bytes"`; ValidBentSamples int `json:"valid_bent_samples"`; UnknownSamples int `json:"unknown_samples"`; Findings []Finding `json:"findings"` }
func key(a,b string) string {return a+"/"+b}
func validPositive(v float64) bool {return !math.IsNaN(v)&&!math.IsInf(v,0)&&v>0}
func evaluate(in Input, sourceBytes []byte) Result {
 r:=Result{Schema:"scp.visualqa.l2_knee_result.v1",Status:"UNKNOWN",SourceSHA256:in.SourceSHA256,Findings:[]Finding{}}
 add:=func(t int64,a,b,sev,why string, cos, flex float64){r.Findings=append(r.Findings,Finding{Frame:t,Actor:a,Leg:b,Severity:sev,Reason:why,SignedPoleCos:cos,FlexDegrees:flex});if sev=="UNKNOWN"{r.UnknownSamples++}}
 if in.Schema!="scp.visualqa.l2_knee_input.v1"||in.Rights!="ORIGINAL_SELF_AUTHORED_SYNTHETIC"||len(in.Legs)<1||len(in.Frames)<2 {add(0,"","","FAIL","INVALID_SCHEMA_RIGHTS_OR_COVERAGE",0,0);r.Status="FAIL";return r}
 sum:=sha256.Sum256(sourceBytes)
 if len(sourceBytes)==0||in.SourceSHA256!=hex.EncodeToString(sum[:]) {add(0,"","","FAIL","SOURCE_HASH_MISMATCH",0,0);r.Status="FAIL";return r}
 r.VerifiedSourceBytes=true
 specs:=map[string]Spec{}
 for _,s:=range in.Legs {
  k:=key(s.Actor,s.Leg)
  if s.Actor==""|| (s.Leg!="Left"&&s.Leg!="Right")||!s.Pole.finite()||s.Pole.norm()<1e-6||!validPositive(s.Upper)||!validPositive(s.Lower)||specs[k].Actor!="" {add(0,s.Actor,s.Leg,"FAIL","INVALID_OR_DUPLICATE_LEG_SPEC",0,0);r.Status="FAIL";return r}
  specs[k]=s
 }
 seenBent:=map[string]bool{}
 failures:=0
 var prior int64
 for i,f:=range in.Frames {
  if (i>0&&f.Tick<=prior)||len(f.Poses)!=len(specs) {add(f.Tick,"","","FAIL","FRAME_CLOCK_OR_COVERAGE",0,0);failures++;continue}
  prior=f.Tick
  used:=map[string]bool{}
  for _,p:=range f.Poses {
   k:=key(p.Actor,p.Leg);s,ok:=specs[k]
   if !ok||used[k]||!p.Hip.finite()||!p.Knee.finite()||!p.Ankle.finite() {add(f.Tick,p.Actor,p.Leg,"FAIL","INVALID_POSE_OR_MISSING_SPEC",0,0);failures++;continue}
   used[k]=true
   upper:=p.Hip.sub(p.Knee)
   lower:=p.Ankle.sub(p.Knee)
   u:=upper.norm();l:=lower.norm()
   if u<1e-7||l<1e-7||math.Abs(u-s.Upper)>0.005||math.Abs(l-s.Lower)>0.005 {add(f.Tick,p.Actor,p.Leg,"FAIL","SEGMENT_LENGTH_MISMATCH",0,0);failures++;continue}
   axis:=p.Ankle.sub(p.Hip)
   axisNorm:=axis.norm()
   if axisNorm<1e-7 {add(f.Tick,p.Actor,p.Leg,"FAIL","DEGENERATE_HIP_ANKLE",0,0);failures++;continue}
   unit:=axis.scale(1/axisNorm)
   bend:=p.Knee.sub(p.Hip)
   bend=bend.sub(unit.scale(bend.dot(unit)))
   pole:=s.Pole.sub(unit.scale(s.Pole.dot(unit)))
   if pole.norm()<1e-7 {add(f.Tick,p.Actor,p.Leg,"UNKNOWN","POLE_PARALLEL_TO_LEG",0,0);continue}
   if bend.norm()<0.004 {add(f.Tick,p.Actor,p.Leg,"UNKNOWN","NEAR_STRAIGHT_NO_KNEE_SIDE_WITNESS",0,0);continue}
   c:=bend.dot(pole)/(bend.norm()*pole.norm())
   raw:=upper.dot(lower)/(u*l)
   raw=math.Max(-1,math.Min(1,raw))
   flex:=180-math.Acos(raw)*180/math.Pi
   if c<0.05 {add(f.Tick,p.Actor,p.Leg,"FAIL","BACKWARD_OR_WRONG_POLE_KNEE_BEND",c,flex);failures++;continue}
   if flex>150 {add(f.Tick,p.Actor,p.Leg,"FAIL","EXCESSIVE_KNEE_FLEXION",c,flex);failures++;continue}
   seenBent[k]=true;r.ValidBentSamples++
  }
  if len(used)!=len(specs){add(f.Tick,"","","FAIL","MISSING_LEG_POSE",0,0);failures++}
 }
 if failures>0 {r.Status="FAIL"} else if len(seenBent)!=len(specs) {r.Status="UNKNOWN";add(0,"","","UNKNOWN","NOT_ALL_LEGS_HAVE_BENT_FRAME",0,0)} else {r.Status="PASS_L2_REST_POLE_GEOMETRY_ONLY"}
 return r
}
func main(){
 input:=flag.String("input","","source-pinned independent pose receipt")
 source:=flag.String("source","","source binary to verify SHA256")
 flag.Parse()
 if *input==""||*source=="" {fmt.Fprintln(os.Stderr,"required --input and --source");os.Exit(3)}
 b,err:=os.ReadFile(*input);if err!=nil {fmt.Fprintln(os.Stderr,err);os.Exit(3)}
 x,err:=os.ReadFile(*source);if err!=nil {fmt.Fprintln(os.Stderr,err);os.Exit(3)}
 var in Input
 if err:=json.Unmarshal(b,&in);err!=nil {fmt.Fprintln(os.Stderr,err);os.Exit(3)}
 r:=evaluate(in,x)
 _=json.NewEncoder(os.Stdout).Encode(r)
 switch r.Status {case "PASS_L2_REST_POLE_GEOMETRY_ONLY":os.Exit(0);case "FAIL":os.Exit(2);default:os.Exit(3)}
}
