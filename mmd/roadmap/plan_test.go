package roadmap

import (
    "encoding/json"
    "os"
    "strings"
    "testing"
)

func baseline(t *testing.T) Workplan {
    t.Helper()
    b,err:=os.ReadFile("workplan.v1.json")
    if err!=nil {t.Fatal(err)}
    got,err:=Decode(b)
    if err!=nil {t.Fatalf("repo workplan must validate: %v",err)}
    return got
}
func TestRepositoryPlan(t *testing.T) {
    w:=baseline(t)
    s:=Summarize(w)
    if s.Total!=21 || s.Counts["BLOCKED"]!=2 ||
       s.Counts["READY"]+s.Counts["BLOCKED"]+s.Counts["PLANNED"]+s.Counts["DONE"]!=s.Total {
       t.Fatalf("roadmap count mismatch: %+v",s.Counts)
    }
    if len(s.Ready)==0 {t.Fatal("no ready work baton")}
    if w.Tasks[0].ID!="W01" {t.Fatal("baseline W01 must preserve stable identity")}
    if !strings.Contains(Markdown(w),"## BLOCKED") {t.Fatal("human representation hid blockers")}
}
func TestRejectUnmetReady(t *testing.T){
    w:=baseline(t)
    for i:=range w.Tasks {if w.Tasks[i].ID=="W05" {w.Tasks[i].Status="READY"}}
    if err:=Validate(w);err==nil {t.Fatal("accepted READY without completed dependencies")}
}
func TestRejectUnqualifiedDone(t *testing.T){
    w:=baseline(t)
    for i:=range w.Tasks {if w.Tasks[i].ID=="W01" {w.Tasks[i].Status="DONE";w.Tasks[i].CompletionEvidence=""}}
    if err:=Validate(w);err==nil {t.Fatal("accepted DONE with no evidence")}
}
func TestAcceptScopedCompletionEvidence(t *testing.T){
    w:=baseline(t)
    for i:=range w.Tasks {if w.Tasks[i].ID=="W01" {
        w.Tasks[i].Status="DONE"
        w.Tasks[i].CompletionEvidence="https://github.com/SemperSupra/stable-character-pipeline/actions/runs/1"
    }}
    if err:=Validate(w);err!=nil {t.Fatalf("should accept independently evidenced completion: %v",err)}
}
func TestRejectCycles(t *testing.T){
    w:=baseline(t)
    for i:=range w.Tasks {if w.Tasks[i].ID=="W01" {
        w.Tasks[i].Status="PLANNED"
        w.Tasks[i].CompletionEvidence=""
        w.Tasks[i].DependsOn=[]string{"W02"}
    }}
    if err:=Validate(w);err==nil || !strings.Contains(err.Error(),"cycle") {
        t.Fatalf("failed to reject hidden dependency cycle: %v",err)
    }
}
func TestRejectUnsafeBoundaries(t *testing.T){
    w:=baseline(t)
    w.Rules.NoAutomaticCPEPromotion=false
    if err:=Validate(w);err==nil {t.Fatal("accepted automated policy promotion")}
    w=baseline(t)
    w.Tasks[0].BudgetUSDCeiling=1
    if err:=Validate(w);err==nil {t.Fatal("accepted metered runner")}
    w=baseline(t)
    w.Tasks[0].Audiences=[]string{"agent"}
    if err:=Validate(w);err==nil {t.Fatal("accepted audience contract bypass")}
}
func TestRejectOrphanBlockedAndUnknownTask(t *testing.T){
    w:=baseline(t)
    for i:=range w.Tasks {if w.Tasks[i].ID=="W19" {w.Tasks[i].Blocker=""}}
    if err:=Validate(w);err==nil {t.Fatal("accepted opaque blocked state")}
    w=baseline(t)
    w.Tasks[0].DependsOn=[]string{"no-such-task"}
    if err:=Validate(w);err==nil {t.Fatal("accepted missing dependency")}
}
func TestStrictJSONAndRoundTrip(t *testing.T){
    w:=baseline(t)
    content,err:=json.Marshal(w)
    if err!=nil {t.Fatal(err)}
    if _,err:=Decode(content);err!=nil {t.Fatalf("roundtrip failed: %v",err)}
    if _,err:=Decode(append(content,[]byte(" {}")...));err==nil {t.Fatal("accepted two JSON documents")}
    // Unknown keys fail closed; docs/schema drift cannot bypass reviewer.
    bad:=strings.Replace(string(content),`"schema":`,`"unknown_secret_override":true,"schema":`,1)
    if _,err:=Decode([]byte(bad));err==nil {t.Fatal("accepted undocumented field")}
}
