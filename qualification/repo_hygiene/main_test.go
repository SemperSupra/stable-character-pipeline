package main
import (
 "encoding/json"
 "errors"
 "fmt"
 "strings"
 "testing"
)
func sha(c string)string{return strings.Repeat(c,40)}
type item struct { n int; base string; baseSHA string; headSHA string; state string; draft bool; merged bool; paths []string; ci string }
func fakeGetter(items []item)Getter {
 data:=map[string]item{}
 for _,v:=range items{data[fmt.Sprint(v.n)]=v}
 return func(path string,dst any)error {
  if strings.HasPrefix(path,"pulls/"){
   var n int
   if _,e:=fmt.Sscanf(path,"pulls/%d",&n);e!=nil{return e}
   v,ok:=data[fmt.Sprint(n)];if !ok{return errors.New("not found")}
   if strings.Contains(path,"/files?"){
    fs:=[]PRFile{}
    for _,p:=range v.paths{fs=append(fs,PRFile{Filename:p,Status:"added"})}
    b,_:=json.Marshal(fs);return json.Unmarshal(b,dst)
   }
   p:=PR{Number:v.n,State:v.state,Draft:v.draft,Merged:v.merged}
   p.Head.Ref=fmt.Sprintf("branch%d",v.n);p.Head.SHA=v.headSHA
   p.Base.Ref=v.base;p.Base.SHA=v.baseSHA
   b,_:=json.Marshal(p);return json.Unmarshal(b,dst)
  }
  if strings.HasPrefix(path,"actions/runs?"){
   var n int
   for _,v:=range items{if strings.Contains(path,"branch=branch"+fmt.Sprint(v.n)+"&"){n=v.n;break}}
   v,ok:=data[fmt.Sprint(n)];if !ok{return errors.New("bad branch")}
   r:=WorkflowRuns{}
   x:=struct{
    ID int64 `json:"id"`
    HeadSHA string `json:"head_sha"`
    Status string `json:"status"`
    Conclusion string `json:"conclusion"`
    HTMLURL string `json:"html_url"`
   }{ID:int64(n),HeadSHA:v.headSHA,Status:"completed",Conclusion:v.ci}
   r.Runs=append(r.Runs,x)
   b,_:=json.Marshal(r);return json.Unmarshal(b,dst)
  }
  return errors.New("unrecognized GET")
 }
}
func basicItems()[]item{
 return []item{
  {n:300,base:"main",baseSHA:sha("a"),headSHA:sha("b"),state:"open",draft:true,paths:[]string{"common.go","contract.go"},ci:"success"},
  {n:301,base:"branch300",baseSHA:sha("b"),headSHA:sha("c"),state:"open",draft:true,paths:[]string{"common.go","viewer.go"},ci:"success"},
  {n:306,base:"branch300",baseSHA:sha("b"),headSHA:sha("d"),state:"open",draft:true,paths:[]string{"viewer.go","policy.go"},ci:"failure"},
  {n:299,base:"main",baseSHA:sha("a"),headSHA:sha("e"),state:"closed",draft:true,paths:[]string{"failed.go"},ci:"failure"},
 }
}
func scope()Scope{return Scope{Schema:"scp.repo_hygiene_scope.v1",Repository:"SemperSupra/stable-character-pipeline",PRs:[]int{306,300,299,301}}}
func TestDeterministicGraphAndHolds(t *testing.T){
 r,e:=build(scope(),fakeGetter(basicItems()));if e!=nil{t.Fatal(e)}
 if r.Summary.Total!=4||r.Summary.OpenDraft!=3||r.Summary.ClosedUnmerged!=1||r.Summary.ExactHeadGreen!=2||r.Summary.CIUnknownOrFail!=2{t.Fatal(r.Summary)}
 if r.Summary.IndependentCollisions!=1||r.Summary.ExpectedStackOverlaps!=1{t.Fatal("misclassified parallel collision / expected ancestor",r.Overlaps)}
 if r.PRs[0].Number!=299||r.PRs[1].Number!=300{t.Fatal("nondeterministic ordering")}
 for _,p:=range r.PRs{if !p.NoAutoPromotion{t.Fatal("unsafe promotion")} }
 if e:=verify(r);e!=nil{t.Fatal(e)}
 rr,e:=build(scope(),fakeGetter(basicItems()));if e!=nil||r.Digest!=rr.Digest{t.Fatal("nonrepeatable snapshot",e)}
}
func TestParentDriftBlocks(t *testing.T){
 items:=basicItems()
 items[1].baseSHA=sha("f")
 r,e:=build(scope(),fakeGetter(items));if e!=nil{t.Fatal(e)}
 if r.Summary.DriftedBases!=1{t.Fatal(r.Summary)}
 for _,p:=range r.PRs{if p.Number==301&&(p.Disposition!="BLOCK_BASE_HEAD_DRIFT_OWNER_REVIEW"||!p.BaseDrift){t.Fatal("stale stack accepted")}}
}
func TestFailClosedInput(t *testing.T){
 s:=scope()
 s.PRs=[]int{299,299}
 if _,e:=build(s,fakeGetter(basicItems()));e==nil{t.Fatal("duplicate scoped PR admitted")}
 s=scope();s.Repository="private/secret"
 if _,e:=build(s,fakeGetter(basicItems()));e==nil{t.Fatal("private repo admitted")}
 s=scope();a:=basicItems();a[0].headSHA="bad"
 if _,e:=build(s,fakeGetter(a));e==nil{t.Fatal("bad head SHA admitted")}
 s=scope();broken:=func(string,any)error{return errors.New("api failure")}
 if _,e:=build(s,broken);e==nil{t.Fatal("lost API treated as success")}
}
func TestReceiptMutationFailsVerification(t *testing.T){
 r,e:=build(scope(),fakeGetter(basicItems()));if e!=nil{t.Fatal(e)}
 r.AutomaticMerges=1
 if verify(r)==nil{t.Fatal("unsafe remote mutation claim")}
 r.AutomaticMerges=0;r.PRs[0].Disposition="SAFE_TO_MERGE"
 if verify(r)==nil{t.Fatal("tampered receipt accepted")}
}
func TestStates(t *testing.T){
 for _,tc:=range []struct{state string;merged,draft bool;want string}{
  {"closed",false,true,"CLOSED_UNMERGED_RETAIN_FIRST_FAILURES"},
  {"closed",true,false,"MERGED_RETAIN_PROVENANCE_UNVERIFIED_ACCEPTANCE"},
  {"open",false,true,"OPEN_DRAFT_RETAIN_OWNER_GATES"},
  {"open",false,false,"OPEN_OWNER_REVIEW_REQUIRED_NO_AUTO_MERGE"},
 }{
  p:=PR{State:tc.state,Merged:tc.merged,Draft:tc.draft}
  if got:=stateDisposition(p);got!=tc.want{t.Fatalf("got %q want %q",got,tc.want)}
 }
}
