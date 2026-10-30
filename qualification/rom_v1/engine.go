// ROM V1: source-hashed, source-only scalar joint limit witness.
// This numerical check is NOT a human/animal anatomy or robotics safety oracle.
package main
import (
 "crypto/sha256"
 "encoding/hex"
 "math"
)
type Joint struct {
 ID string `json:"id"`
 Kind string `json:"kind"`
 Unit string `json:"unit"`
 Frame string `json:"frame"`
 Provenance string `json:"provenance"`
 Min *float64 `json:"hard_min,omitempty"`
 Max *float64 `json:"hard_max,omitempty"`
 SoftMin *float64 `json:"soft_min,omitempty"`
 SoftMax *float64 `json:"soft_max,omitempty"`
 Velocity *float64 `json:"max_velocity,omitempty"`
 Acceleration *float64 `json:"max_acceleration,omitempty"`
 Jerk *float64 `json:"max_jerk,omitempty"`
 Effort *float64 `json:"max_effort,omitempty"`
}
type Coupling struct {
 Master string `json:"master"`
 Slave string `json:"slave"`
 Multiplier float64 `json:"multiplier"`
 Offset float64 `json:"offset"`
 Tolerance float64 `json:"tolerance"`
 Provenance string `json:"provenance"`
}
type Frame struct {
 Tick int64 `json:"tick"`
 Q map[string]float64 `json:"q"`
 Effort map[string]float64 `json:"effort,omitempty"`
}
type Input struct {
 Schema string `json:"schema"`
 Rights string `json:"rights"`
 SourceSHA256 string `json:"source_sha256"`
 Morphology string `json:"morphology"`
 Context string `json:"context"`
 RateNum int64 `json:"rate_num"`
 RateDen int64 `json:"rate_den"`
 Joints []Joint `json:"joints"`
 Couplings []Coupling `json:"couplings,omitempty"`
 Frames []Frame `json:"frames"`
}
type Finding struct {
 Tick int64 `json:"tick"`
 Joint string `json:"joint"`
 Severity string `json:"severity"`
 Code string `json:"code"`
}
type Result struct {
 Schema string `json:"schema"`
 Status string `json:"status"`
 VerifiedSourceBytes bool `json:"verified_source_bytes"`
 SourceSHA256 string `json:"source_sha256"`
 Morphology string `json:"morphology"`
 Findings []Finding `json:"findings"`
 AnatomyAcceptance string `json:"anatomy_acceptance"`
}
func finite(x float64) bool {return !math.IsNaN(x)&&!math.IsInf(x,0)}
func positive(p *float64) bool {return p!=nil&&finite(*p)&&*p>0}
func evaluate(in Input,source []byte) Result {
 r:=Result{Schema:"scp.rom.v1_result",Status:"UNKNOWN",SourceSHA256:in.SourceSHA256,
 Morphology:in.Morphology,AnatomyAcceptance:"NOT_QUALIFIED",Findings:[]Finding{}}
 fails,unknown:=0,0
 add:=func(tick int64,joint,severity,code string){
  r.Findings=append(r.Findings,Finding{Tick:tick,Joint:joint,Severity:severity,Code:code})
  if severity=="FAIL"{fails++}else if severity=="UNKNOWN"{unknown++}
 }
 if in.Schema!="scp.rom.v1_input"||in.Rights!="ORIGINAL_SELF_AUTHORED_SYNTHETIC"||
 len(source)==0||len(in.Joints)==0||len(in.Frames)<4||in.Context==""||
 in.RateNum<1||in.RateDen<1||in.RateNum>1000000||in.RateDen>1000000{
  add(0,"","FAIL","SCHEMA_RIGHTS_OR_COVERAGE");r.Status="FAIL";return r
 }
 h:=sha256.Sum256(source)
 if in.SourceSHA256!=hex.EncodeToString(h[:]){
  add(0,"","FAIL","SOURCE_SHA_MISMATCH");r.Status="FAIL";return r
 }
 r.VerifiedSourceBytes=true
 if in.Morphology!="synthetic_fixture"&&in.Morphology!="human"&&in.Morphology!="animal"&&in.Morphology!="machine"&&in.Morphology!="designed_other"{
  add(0,"","FAIL","MORPHOLOGY_INVALID")
 } else if in.Morphology!="synthetic_fixture"{
  add(0,"","UNKNOWN","BIOLOGICAL_OR_MECHANISM_LIMITS_UNADMITTED")
 }
 joints:=map[string]Joint{}
 for _,j:=range in.Joints{
  if j.ID==""||j.Frame==""||j.Provenance==""||joints[j.ID].ID!=""{
   add(0,j.ID,"FAIL","JOINT_ID_FRAME_OR_PROVENANCE");continue
  }
  valid:=(j.Kind=="revolute"&&j.Unit=="rad")||(j.Kind=="prismatic"&&j.Unit=="m")||
   (j.Kind=="continuous"&&j.Unit=="rad")
  if !valid {add(0,j.ID,"FAIL","KIND_AND_UNITS_INVALID");continue}
  if j.Frame!="PARENT_LOCAL_TEST_ONLY"||j.Provenance!="SYNTHETIC_TEST_ONLY"{
   add(0,j.ID,"UNKNOWN","FRAME_OR_PROVENANCE_UNADMITTED")
  }
  if j.Kind=="continuous" {
   if j.Min!=nil||j.Max!=nil{add(0,j.ID,"FAIL","CONTINUOUS_CANNOT_HAVE_HARD_STOPS")}
   add(0,j.ID,"UNKNOWN","CONTINUOUS_ANGLE_UNWRAP_UNQUALIFIED")
  }else if j.Min==nil||j.Max==nil||!finite(*j.Min)||!finite(*j.Max)||*j.Min>=*j.Max{
   add(0,j.ID,"FAIL","HARD_RANGE_INVALID")
  }else if j.SoftMin!=nil||j.SoftMax!=nil{
   if j.SoftMin==nil||j.SoftMax==nil||!finite(*j.SoftMin)||!finite(*j.SoftMax)||
    *j.SoftMin<*j.Min||*j.SoftMax>*j.Max||*j.SoftMin>*j.SoftMax{
    add(0,j.ID,"FAIL","SOFT_RANGE_INVALID")
   }
  }
  if !positive(j.Velocity)||!positive(j.Acceleration)||!positive(j.Jerk){
   add(0,j.ID,"UNKNOWN","DYNAMIC_ENVELOPE_INCOMPLETE")
  }
  if j.Effort!=nil&&!positive(j.Effort){add(0,j.ID,"FAIL","EFFORT_LIMIT_INVALID")}
  if in.Morphology=="machine"&&j.Effort==nil{add(0,j.ID,"UNKNOWN","ACTUATOR_EFFORT_MISSING")}
  joints[j.ID]=j
 }
 if len(joints)!=len(in.Joints){add(0,"","FAIL","JOINT_COVERAGE_INVALID")}
 for _,c:=range in.Couplings{
  master,okm:=joints[c.Master];slave,oks:=joints[c.Slave]
  if !okm||!oks||master.Unit!=slave.Unit||c.Master==c.Slave||
   !finite(c.Multiplier)||!finite(c.Offset)||!finite(c.Tolerance)||c.Tolerance<0{
   add(0,c.Slave,"FAIL","COUPLING_DEFINITION_INVALID")
  }else if c.Provenance!="SYNTHETIC_TEST_ONLY"{
   add(0,c.Slave,"UNKNOWN","COUPLING_EVIDENCE_UNADMITTED")
  }
 }
 if fails>0{r.Status="FAIL";return r}
 for i,f:=range in.Frames{
  if (i==0&&f.Tick!=0)||(i>0&&f.Tick<=in.Frames[i-1].Tick)||len(f.Q)!=len(in.Joints){
   add(f.Tick,"","FAIL","CLOCK_OR_POSITION_COVERAGE");continue
  }
  for _,j:=range in.Joints{
   q,ok:=f.Q[j.ID]
   if !ok||!finite(q){add(f.Tick,j.ID,"FAIL","POSITION_NOT_OBSERVED");continue}
   if j.Min!=nil&&j.Max!=nil&&(q<*j.Min-1e-10||q>*j.Max+1e-10){
    add(f.Tick,j.ID,"FAIL","HARD_ROM_VIOLATION")
   }else if j.SoftMin!=nil&&j.SoftMax!=nil&&(q<*j.SoftMin||q>*j.SoftMax){
    add(f.Tick,j.ID,"WARN","SOFT_MARGIN")
   }
   if j.Effort!=nil{
    effort,ok:=f.Effort[j.ID]
    if !ok{add(f.Tick,j.ID,"UNKNOWN","EFFORT_OBSERVATION_MISSING")
    }else if !finite(effort)||math.Abs(effort)>*j.Effort+1e-10{
     add(f.Tick,j.ID,"FAIL","EFFORT_LIMIT_VIOLATION")
    }
   }
  }
  for _,c:=range in.Couplings{
   master,okm:=f.Q[c.Master];slave,oks:=f.Q[c.Slave]
   if okm&&oks&&math.Abs(slave-(c.Multiplier*master+c.Offset))>c.Tolerance+1e-10{
    add(f.Tick,c.Slave,"FAIL","JOINT_COUPLING_VIOLATION")
   }
  }
 }
 for _,j:=range in.Joints{
  velocities,midtimes:=[]float64{},[]float64{}
  for i:=1;i<len(in.Frames);i++{
   a,b:=in.Frames[i-1],in.Frames[i]
   if b.Tick<=a.Tick{continue}
   delta:=float64(b.Tick-a.Tick)*float64(in.RateDen)/float64(in.RateNum)
   v:=(b.Q[j.ID]-a.Q[j.ID])/delta
   velocities=append(velocities,v)
   midtimes=append(midtimes,float64(a.Tick+b.Tick)*float64(in.RateDen)/(2*float64(in.RateNum)))
   if j.Velocity!=nil&&math.Abs(v)>*j.Velocity+1e-10{add(b.Tick,j.ID,"FAIL","VELOCITY_LIMIT")}
  }
  accelerations,atimes:=[]float64{},[]float64{}
  for i:=1;i<len(velocities);i++{
   dt:=midtimes[i]-midtimes[i-1]
   if dt<=0{continue}
   a:=(velocities[i]-velocities[i-1])/dt
   accelerations=append(accelerations,a)
   atimes=append(atimes,(midtimes[i]+midtimes[i-1])/2)
   if j.Acceleration!=nil&&math.Abs(a)>*j.Acceleration+1e-10{
    add(in.Frames[i+1].Tick,j.ID,"FAIL","ACCELERATION_LIMIT")
   }
  }
  for i:=1;i<len(accelerations);i++{
   dt:=atimes[i]-atimes[i-1]
   if dt<=0{continue}
   jerk:=(accelerations[i]-accelerations[i-1])/dt
   if j.Jerk!=nil&&math.Abs(jerk)>*j.Jerk+1e-10{
    add(in.Frames[i+2].Tick,j.ID,"FAIL","JERK_LIMIT")
   }
  }
 }
 if fails>0{r.Status="FAIL"}else if unknown>0{r.Status="UNKNOWN"
 }else{r.Status="PASS_SYNTHETIC_SCALAR_LIMITS_ONLY"}
 return r
}