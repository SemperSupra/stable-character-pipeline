package main

import (
 "context"
 "errors"
 "strings"
 "testing"
)
func fixtureForDrift() (Snapshot,Workset,error){
 s:=rootFixture()
 s.PRs[2].Base.SHA=strings.Repeat("f",40)
 ws,err:=buildWorkset(s)
 return s,ws,err
}
func cannedComparison(pathsParent,pathsChild []string) compareFunc {
 return func(_ context.Context,base,head string)(CompareResponse,error){
  old:=strings.Repeat("f",40)
  parent:=strings.Repeat("b",40)
  child:=strings.Repeat("c",40)
  if base==old&&head==parent{
   out:=CompareResponse{Status:"ahead",AheadBy:2,BehindBy:0}
   for _,p:=range pathsParent{out.Files=append(out.Files,CompareFile{Filename:p})}
   return out,nil
  }
  if base==old&&head==child{
   out:=CompareResponse{Status:"ahead",AheadBy:7,BehindBy:0}
   for _,p:=range pathsChild{out.Files=append(out.Files,CompareFile{Filename:p})}
   return out,nil
  }
  if base==parent&&head==child{
   return CompareResponse{Status:"diverged",AheadBy:7,BehindBy:2,
    MergeBaseCommit:CompareRef{SHA:old}},nil
  }
  return CompareResponse{},errors.New("unexpected commit compare")
 }
}
func TestSourceDivergenceCategorizationNoApply(t *testing.T){
 s,ws,e:=fixtureForDrift();if e!=nil{t.Fatal(e)}
 // Child #292 old base f..., parent #291 current b..., child current c...
 for _,caseFiles:=range []struct{parent,child []string;classification string}{
  {[]string{"a.go"},[]string{"b.go"},"DISJOINT_PATHS_REVIEW_ONLY"},
  {[]string{"same.go"},[]string{"same.go","unrelated.go"},"SHARED_PATHS_CONFLICT_REVIEW"},
 }{
  got,err:=inspectDrifts(context.Background(),s,ws,cannedComparison(caseFiles.parent,caseFiles.child))
  if err!=nil{t.Fatal(err)}
  if got.Count!=1||got.Mutations!=0||got.OwnerApproval||got.Reviews[0].Classification!=caseFiles.classification{
   t.Fatalf("wrong conservative disposition: %#v",got)
  }
  if !strings.Contains(got.Markdown(),caseFiles.classification) {t.Fatal("no visible independent evidence")}
  if got.Reviews[0].Action!="RETAIN_UNMERGED_OWNER_AND_EXACT_CI_REVIEW_REQUIRED"{t.Fatal("unsafe promotion")}
 }
}
func TestSourceHistoryRewriteMustRemainHeld(t *testing.T){
 s,ws,e:=fixtureForDrift();if e!=nil{t.Fatal(e)}
 fake:=func(_ context.Context,base,head string)(CompareResponse,error){
  return CompareResponse{Status:"diverged",AheadBy:1,BehindBy:1,
   MergeBaseCommit:CompareRef{SHA:strings.Repeat("0",40)}},nil
 }
 report,err:=inspectDrifts(context.Background(),s,ws,fake)
 if err!=nil{t.Fatal(err)}
 if report.Reviews[0].Classification!="HISTORY_UNVERIFIED_HELD"{t.Fatal(report)}
}
func TestCompareFailureAndTruncatedFilesFailClosed(t *testing.T){
 s,ws,e:=fixtureForDrift();if e!=nil{t.Fatal(e)}
 _,err:=inspectDrifts(context.Background(),s,ws,
   func(context.Context,string,string)(CompareResponse,error){return CompareResponse{},errors.New("upstream 503")})
 if err==nil{t.Fatal("missing remote evidence accepted")}
 huge:=make([]CompareFile,300)
 for i:=range huge{huge[i]=CompareFile{Filename:"a.go"}}
 _,err=distinctPaths(huge)
 if err==nil{t.Fatal("first-page compare truncation accepted")}
 if _,err=distinctPaths([]CompareFile{{Filename:"x\nfake"}});err==nil{t.Fatal("injected filename accepted")}
}
func TestStaleDriftHeadAndWrongRepositoryFailClosed(t *testing.T){
 s,ws,e:=fixtureForDrift();if e!=nil{t.Fatal(e)}
 s.PRs[1].Head.SHA=strings.Repeat("a",40)
 _,err:=inspectDrifts(context.Background(),s,ws,cannedComparison(nil,nil))
 if err==nil{t.Fatal("stale source accepted")}
 s,ws,e=fixtureForDrift();if e!=nil{t.Fatal(e)}
 s.Repo="SemperSupra/stable-character-pipeline-private"
 _,err=inspectDrifts(context.Background(),s,ws,cannedComparison(nil,nil))
 if err==nil{t.Fatal("private source allowed")}
}
