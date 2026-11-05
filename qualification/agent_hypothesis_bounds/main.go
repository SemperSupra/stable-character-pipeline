// Bounded actor-generated parameter plans. Never runs an optimizer or writes a mesh.
package main

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "math"
 "os"
 "regexp"
)
var shaRE = regexp.MustCompile(`^[0-9a-f]{64}$`)
var idRE = regexp.MustCompile(`^[a-z][a-z0-9_]{2,63}$`)
type Proposal struct {
 Schema string `json:"schema"`
 ExperimentID string `json:"experiment_id"`
 SubjectClass string `json:"subject_class"`
 BaselineSHA256 string `json:"baseline_sha256"`
 ReferenceSHA256 string `json:"reference_sha256"`
 Joint string `json:"joint"`
 Axis string `json:"axis"`
 MinRadians float64 `json:"min_radians"`
 MaxRadians float64 `json:"max_radians"`
 Candidates int `json:"candidates"`
 EvidenceClass string `json:"evidence_class"`
 Intent string `json:"intent"`
}
type Candidate struct {
 Index int `json:"index"`
 AngleRadians float64 `json:"angle_radians"`
 CandidateID string `json:"candidate_id"`
}
type Plan struct {
 Schema string `json:"schema"`
 ExperimentID string `json:"experiment_id"`
 Joint string `json:"joint"`
 Axis string `json:"axis"`
 BaselineSHA256 string `json:"baseline_sha256"`
 ReferenceSHA256 string `json:"reference_sha256"`
 CandidatePlans []Candidate `json:"candidate_plans"`
 Disposition string `json:"disposition"`
 Limits string `json:"limits"`
 Execution bool `json:"execution"`
}
func scanKeys(d *json.Decoder)error{
 t,e:=d.Token();if e!=nil{return e}
 delim,ok:=t.(json.Delim);if !ok{return nil}
 switch delim{
 case '{':
  seen:=map[string]bool{}
  for d.More(){
   x,e:=d.Token();if e!=nil{return e}
   k,ok:=x.(string);if !ok{return errors.New("invalid key")}
   if seen[k]{return fmt.Errorf("duplicate JSON key %q",k)}
   seen[k]=true
   if e:=scanKeys(d);e!=nil{return e}
  }
  _,e:=d.Token();return e
 case '[':
  for d.More(){if e:=scanKeys(d);e!=nil{return e}}
  _,e:=d.Token();return e
 default:return errors.New("invalid delimiter")
 }
}
func decode(raw []byte)(Proposal,error){
 var p Proposal
 if len(raw)==0||len(raw)>1<<20{return p,errors.New("JSON out of bounds")}
 d:=json.NewDecoder(bytes.NewReader(raw))
 if e:=scanKeys(d);e!=nil{return p,e}
 if _,e:=d.Token();e!=io.EOF{return p,errors.New("trailing input")}
 d=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 if e:=d.Decode(&p);e!=nil{return p,e}
 if _,e:=d.Token();e!=io.EOF{return p,errors.New("trailing input")}
 return p,validate(p)
}
func finite(v float64)bool{return !math.IsNaN(v)&&!math.IsInf(v,0)}
func validate(p Proposal)error{
 if p.Schema!="scp.actor_parameter_plan.v1"||!idRE.MatchString(p.ExperimentID){return errors.New("invalid schema or experiment ID")}
 if p.SubjectClass!="public_original_synthetic_equine"{return errors.New("private/unsupported subject class")}
 if !shaRE.MatchString(p.BaselineSHA256)||!shaRE.MatchString(p.ReferenceSHA256)||p.BaselineSHA256==p.ReferenceSHA256{return errors.New("invalid or reused source hashes")}
 if p.Joint!="neck"||p.Axis!="Z"{return errors.New("only frozen source neck/Z admitted in v1")}
 if !finite(p.MinRadians)||!finite(p.MaxRadians)||p.MinRadians < -0.75||p.MaxRadians > 0.75||p.MinRadians >= p.MaxRadians{return errors.New("invalid or dangerous radians")}
 if p.Candidates!=3{return errors.New("exactly three bounded candidates required")}
 if p.EvidenceClass!="public_original_synthetic_self_reference"{return errors.New("unadmitted evidence class")}
 if p.Intent!="candidate_only"{return errors.New("no model mutation or promotion authorization")}
 return nil
}
func plan(p Proposal)Plan{
 mid:=(p.MinRadians+p.MaxRadians)/2
 vals:=[]float64{p.MinRadians,mid,p.MaxRadians}
 result:=Plan{Schema:"scp.actor_candidate_plan.v1",ExperimentID:p.ExperimentID,Joint:p.Joint,Axis:p.Axis,BaselineSHA256:p.BaselineSHA256,ReferenceSHA256:p.ReferenceSHA256,Disposition:"VALID_PLAN_ONLY",Limits:"three neck/Z angles <=0.75rad; no execution; source-render calibration required",Execution:false}
 for i,angle:=range vals{
  wire:=fmt.Sprintf("%s|%s|%s|%s|%s|%d|%.17g",p.ExperimentID,p.BaselineSHA256,p.ReferenceSHA256,p.Joint,p.Axis,i,angle)
  h:=sha256.Sum256([]byte(wire))
  result.CandidatePlans=append(result.CandidatePlans,Candidate{Index:i,AngleRadians:angle,CandidateID:hex.EncodeToString(h[:])})
 }
 return result
}
func main(){
 if len(os.Args)==2&&os.Args[1]=="capabilities"{
  fmt.Println(`{"schema":"scp.actor_parameter_capabilities.v1","operations":["plan"],"model_mutation":false,"runner":false}`);return
 }
 if len(os.Args)!=3||os.Args[1]!="plan"{fmt.Fprintln(os.Stderr,"usage: paramplan capabilities | plan proposal.json");os.Exit(2)}
 raw,e:=os.ReadFile(os.Args[2]);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
 p,e:=decode(raw);if e!=nil{fmt.Fprintln(os.Stderr,"REJECT_PROPOSAL:",e);os.Exit(2)}
 if e:=json.NewEncoder(os.Stdout).Encode(plan(p));e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
}
