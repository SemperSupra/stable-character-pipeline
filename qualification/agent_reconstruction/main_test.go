package main
import ("encoding/json";"strings";"testing")
func h(c string)string{return strings.Repeat(c,64)}
func goodP()Proposal{return Proposal{Schema:"scp.agent_experiment.v1",ID:"synthetic_pony_trial",Baseline:h("a"),Subject:"public_original_synthetic_equine",Evidence:[]string{h("b")},Operation:"rig.optimize",Region:"left_forelimb",Hypothesis:"Carpal skin weights differ from expected values",Budget:Budget{Candidates:3,Seconds:120,MemoryMiB:512},Intent:"candidate_only"}}
func goodR()Report{return Report{Schema:"scp.independent_measurements.v1",ID:"synthetic_pony_trial",Baseline:h("a"),Candidate:h("c"),Evidence:h("b"),Producer:"independent_verifier",Metrics:Metrics{BaselineIoU:0.72,CandidateIoU:0.77,BaselineStrain:0.28,CandidateStrain:0.23,GeometryValid:true,RigValid:true}}}
func TestPositive(t *testing.T){
 p:=goodP();if e:=validate(p);e!=nil{t.Fatal(e)}
 r:=goodR();if e:=checkReport(p,r);e!=nil{t.Fatal(e)}
 d:=review(p,r);if d.Disposition!="PROVISIONAL_FOR_OWNER_REVIEW"||d.Mutations!=0||d.Promotions!=0{t.Fatal(d)}
}
func TestRejectProposal(t *testing.T){
 cases:=[]struct{name string;f func(*Proposal)}{
 {"private",func(p *Proposal){p.Subject="private_human"}},
 {"command",func(p *Proposal){p.Operation="shell.exec"}},
 {"budget",func(p *Proposal){p.Budget.Seconds=10000}},
 {"promotion",func(p *Proposal){p.Intent="promote"}},
 {"bad hash",func(p *Proposal){p.Baseline="missing"}},
 {"duplicate",func(p *Proposal){p.Evidence=append(p.Evidence,p.Evidence[0])}},
 {"injection",func(p *Proposal){p.Region="../private"}},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){p:=goodP();tc.f(&p);if validate(p)==nil{t.Fatal("invalid proposal accepted")}})}
}
func TestJSONStrict(t *testing.T){
 raw,_:=json.Marshal(goodP());var p Proposal;if e:=strict(raw,&p);e!=nil{t.Fatal(e)}
 for _,bad:=range []string{string(raw)+" {}",`{"schema":"a","schema":"b"}`,`{"x":{"k":1,"k":2}}`,`{"invalid":true}`}{if strict([]byte(bad),&p)==nil{t.Fatal("bad JSON accepted")}}
}
func TestRejectReport(t *testing.T){
 p:=goodP()
 for _,tc:=range []struct{name string;f func(*Report)}{
 {"self",func(r *Report){r.Producer="actor"}},
 {"stale",func(r *Report){r.Baseline=h("d")}},
 {"unadmitted",func(r *Report){r.Evidence=h("d")}},
 {"same",func(r *Report){r.Candidate=h("a")}},
 {"bad metric",func(r *Report){r.Metrics.CandidateIoU=1.2}},
 }{t.Run(tc.name,func(t *testing.T){r:=goodR();tc.f(&r);if checkReport(p,r)==nil{t.Fatal("bad report accepted")}})}
}
func TestRegressions(t *testing.T){
 p:=goodP();r:=goodR();r.Metrics.CandidateIoU=0.60
 if review(p,r).Disposition!="REJECT_CANDIDATE"{t.Fatal("IoU regression")}
 r=goodR();r.Metrics.CandidateStrain=0.60
 if review(p,r).Disposition!="REJECT_CANDIDATE"{t.Fatal("strain regression")}
 r=goodR();r.Metrics.RigValid=false
 if review(p,r).Disposition!="REJECT_CANDIDATE"{t.Fatal("rig invalid")}
 r=goodR();r.Metrics.CandidateIoU=0.725
 if review(p,r).Disposition!="UNKNOWN_REQUIRES_INDEPENDENT_EVIDENCE"{t.Fatal("insufficient improvement")}
}
