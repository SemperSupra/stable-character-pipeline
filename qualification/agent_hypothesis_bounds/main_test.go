package main
import ("encoding/json";"strings";"testing")
func sha(c string)string{return strings.Repeat(c,64)}
func valid()Proposal{return Proposal{Schema:"scp.actor_parameter_plan.v1",ExperimentID:"synthetic_pony_neck_fit",SubjectClass:"public_original_synthetic_equine",BaselineSHA256:sha("a"),ReferenceSHA256:sha("b"),Joint:"neck",Axis:"Z",MinRadians:-0.6,MaxRadians:0.6,Candidates:3,EvidenceClass:"public_original_synthetic_self_reference",Intent:"candidate_only"}}
func TestDeterministicBoundedPlan(t *testing.T){
 p:=valid();if e:=validate(p);e!=nil{t.Fatal(e)}
 a,b:=plan(p),plan(p);if len(a.CandidatePlans)!=3||a.Disposition!="VALID_PLAN_ONLY"||a.Execution{t.Fatal(a)}
 for i,v:=range []float64{-0.6,0.0,0.6}{
  if a.CandidatePlans[i].AngleRadians!=v||a.CandidatePlans[i].CandidateID!=b.CandidatePlans[i].CandidateID{t.Fatalf("wrong deterministic plan %+v",a)}
 }
 if a.CandidatePlans[0].CandidateID==a.CandidatePlans[1].CandidateID{t.Fatal("duplicate IDs")}
}
func TestAdversarial(t *testing.T){
 for _,c:=range []struct{name string;edit func(*Proposal)}{
  {"private",func(p *Proposal){p.SubjectClass="protected_human"}},
  {"bad_operation",func(p *Proposal){p.Joint="root"}},
  {"axis",func(p *Proposal){p.Axis="Y"}},
  {"unbounded",func(p *Proposal){p.MaxRadians=3.14}},
  {"inverted",func(p *Proposal){p.MinRadians=0.7;p.MaxRadians=0.1}},
  {"overbudget",func(p *Proposal){p.Candidates=300}},
  {"source",func(p *Proposal){p.ReferenceSHA256="bad"}},
  {"alias",func(p *Proposal){p.ReferenceSHA256=p.BaselineSHA256}},
  {"unadmitted",func(p *Proposal){p.EvidenceClass="real_person_photo"}},
  {"promote",func(p *Proposal){p.Intent="promote"}},
  {"path_injection",func(p *Proposal){p.ExperimentID="../oops"}},
 }{t.Run(c.name,func(t *testing.T){p:=valid();c.edit(&p);if validate(p)==nil{t.Fatal("unsafe proposal accepted")}})}
}
func TestStrictJSON(t *testing.T){
 raw,e:=json.Marshal(valid());if e!=nil{t.Fatal(e)}
 if _,e=decode(raw);e!=nil{t.Fatal(e)}
 for _,bad:=range []string{string(raw)+" {}",`{"schema":"a","schema":"b"}`,`{"foo":{"x":1,"x":2}}`,`{"unknown":true}`}{if _,e:=decode([]byte(bad));e==nil{t.Fatal("invalid JSON accepted")}}
}
