package main

// Candidate-only, source-neutral agent reconstruction contract.
// The CLI validates proposals and submitted measurements; it executes no tools.
import (
 "bytes"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"
 "regexp"
 "strings"
)
var hashRE=regexp.MustCompile(`^[0-9a-f]{64}$`)
var nameRE=regexp.MustCompile(`^[a-z][a-z0-9_]{2,63}$`)
var allowed=map[string]bool{"shape.fit":true,"rig.optimize":true,"motion.fit":true,"render.compare":true}
var subjects=map[string]bool{"public_original_synthetic_human":true,"public_original_synthetic_equine":true}
type Budget struct {
 Candidates int `json:"max_candidates"`
 Seconds int `json:"max_seconds"`
 MemoryMiB int `json:"max_memory_mib"`
}
type Proposal struct {
 Schema string `json:"schema"`
 ID string `json:"experiment_id"`
 Baseline string `json:"baseline_sha256"`
 Subject string `json:"subject_class"`
 Evidence []string `json:"evidence_sha256"`
 Operation string `json:"operation"`
 Region string `json:"region"`
 Hypothesis string `json:"hypothesis"`
 Budget Budget `json:"budget"`
 Intent string `json:"intent"`
}
type Metrics struct {
 BaselineIoU float64 `json:"heldout_iou_baseline"`
 CandidateIoU float64 `json:"heldout_iou_candidate"`
 BaselineStrain float64 `json:"strain_p99_baseline"`
 CandidateStrain float64 `json:"strain_p99_candidate"`
 GeometryValid bool `json:"geometry_valid"`
 RigValid bool `json:"rig_valid"`
}
type Report struct {
 Schema string `json:"schema"`
 ID string `json:"experiment_id"`
 Baseline string `json:"baseline_sha256"`
 Candidate string `json:"candidate_sha256"`
 Evidence string `json:"evidence_sha256"`
 Producer string `json:"producer"`
 Metrics Metrics `json:"measurements"`
}
type Decision struct {
 Schema string `json:"schema"`
 ID string `json:"experiment_id"`
 Disposition string `json:"disposition"`
 Detail string `json:"detail"`
 Mutations int `json:"mutations"`
 Promotions int `json:"model_promotions"`
}
func strict(b []byte, out any) error {
 if len(b)==0||len(b)>1<<20{return errors.New("input length outside [1,1048576]")}
 d:=json.NewDecoder(bytes.NewReader(b))
 if e:=checkKeys(d);e!=nil{return e}
 if _,e:=d.Token();e!=io.EOF{return errors.New("trailing JSON")}
 d=json.NewDecoder(bytes.NewReader(b));d.DisallowUnknownFields()
 if e:=d.Decode(out);e!=nil{return e}
 if _,e:=d.Token();e!=io.EOF{return errors.New("trailing JSON")}
 return nil
}
func checkKeys(d *json.Decoder) error{
 x,e:=d.Token();if e!=nil{return e}
 z,ok:=x.(json.Delim);if !ok{return nil}
 switch z{
 case '{':
  seen:=map[string]bool{}
  for d.More(){
   x,e:=d.Token();if e!=nil{return e}
   k,ok:=x.(string);if !ok{return errors.New("invalid object key")}
   if seen[k]{return errors.New("duplicate JSON key: "+k)}
   seen[k]=true
   if e:=checkKeys(d);e!=nil{return e}
  }
  _,e:=d.Token();return e
 case '[':
  for d.More(){if e:=checkKeys(d);e!=nil{return e}}
  _,e:=d.Token();return e
 default:return errors.New("invalid JSON nesting")
 }
}
func validate(p Proposal) error {
 if p.Schema!="scp.agent_experiment.v1"{return errors.New("schema mismatch")}
 if !nameRE.MatchString(p.ID)||!hashRE.MatchString(p.Baseline){return errors.New("invalid ID/baseline")}
 if !subjects[p.Subject]{return errors.New("only source-original public synthetic subjects")}
 if !allowed[p.Operation]{return errors.New("operation not allowlisted")}
 if !nameRE.MatchString(p.Region)||len(strings.TrimSpace(p.Hypothesis))<12||len(p.Hypothesis)>512{return errors.New("hypothesis/region invalid")}
 if p.Intent!="candidate_only"{return errors.New("no promotion or mutation authorization")}
 if p.Budget.Candidates<1||p.Budget.Candidates>3||p.Budget.Seconds<1||p.Budget.Seconds>300||p.Budget.MemoryMiB<64||p.Budget.MemoryMiB>2048{return errors.New("budget exceeded")}
 if len(p.Evidence)==0||len(p.Evidence)>32{return errors.New("evidence count invalid")}
 seen:=map[string]bool{}
 for _,v:=range p.Evidence{if !hashRE.MatchString(v)||seen[v]{return errors.New("invalid/duplicate evidence hash")};seen[v]=true}
 return nil
}
func checkReport(p Proposal,r Report) error{
 if r.Schema!="scp.independent_measurements.v1"||r.ID!=p.ID||r.Baseline!=p.Baseline{return errors.New("stale report")}
 if !hashRE.MatchString(r.Candidate)||r.Candidate==p.Baseline{return errors.New("candidate must differ from baseline")}
 found:=false;for _,v:=range p.Evidence{if v==r.Evidence{found=true}}
 if !found||r.Producer!="independent_verifier"{return errors.New("unadmitted evidence or self report")}
 m:=r.Metrics
 for _,v:=range []float64{m.BaselineIoU,m.CandidateIoU,m.BaselineStrain,m.CandidateStrain}{if v<0||v>1{return errors.New("metrics out of normalized range")}}
 return nil
}
func review(p Proposal,r Report)Decision{
 d:=Decision{Schema:"scp.agent_decision.v1",ID:p.ID,Disposition:"UNKNOWN_REQUIRES_INDEPENDENT_EVIDENCE",Detail:"insufficient improvement",Mutations:0,Promotions:0}
 m:=r.Metrics
 if !m.GeometryValid||!m.RigValid||m.CandidateIoU+0.0001<m.BaselineIoU||m.CandidateStrain>m.BaselineStrain+0.01{
  d.Disposition="REJECT_CANDIDATE";d.Detail="invalid structure or regression";return d
 }
 if m.CandidateIoU-m.BaselineIoU>=0.01{
  d.Disposition="PROVISIONAL_FOR_OWNER_REVIEW";d.Detail="reported numerical improvement only; independent verifier identity, real imagery and anatomy not authenticated"
 }
 return d
}
func main(){
 if len(os.Args)==2&&os.Args[1]=="capabilities"{
  fmt.Println(`{"schema":"scp.agent_capabilities.v1","actions":["validate","evaluate"],"execution":false,"promotion":false}`);return
 }
 if len(os.Args)<3||len(os.Args)>4||(os.Args[1]!="validate"&&os.Args[1]!="evaluate"){
  fmt.Fprintln(os.Stderr,"usage: contract capabilities | validate proposal.json | evaluate proposal.json report.json");os.Exit(2)
 }
 b,e:=os.ReadFile(os.Args[2]);if e!=nil{panic(e)}
 var p Proposal
 if e=strict(b,&p);e==nil{e=validate(p)}
 if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
 d:=Decision{Schema:"scp.agent_decision.v1",ID:p.ID,Disposition:"VALID_PLAN_ONLY",Detail:"no execution authorized"}
 if os.Args[1]=="evaluate"{
  if len(os.Args)!=4{os.Exit(2)}
  b,e=os.ReadFile(os.Args[3]);if e!=nil{panic(e)}
  var r Report
  if e=strict(b,&r);e==nil{e=checkReport(p,r)}
  if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
  d=review(p,r)
 } else if len(os.Args)!=3{os.Exit(2)}
 _=json.NewEncoder(os.Stdout).Encode(d)
}
