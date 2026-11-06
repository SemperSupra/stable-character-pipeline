package main

import (
 "context"
 "errors"
 "strings"
 "testing"
 "time"
)

func TestLeafRootReachabilityConservative(t *testing.T){
 s:=rootFixture()
 s.PRs=append(s.PRs,Pull{Number:2,Title:"unrelated root",State:"open",
  Draft:true,UpdatedAt:time.Date(2026,11,5,0,0,0,0,time.UTC),
  Head:CommitRef{Ref:"independent",SHA:strings.Repeat("f",40)},
  Base:CommitRef{Ref:"main",SHA:strings.Repeat("e",40)}})
 w,e:=buildWorkset(s);if e!=nil{t.Fatal(e)}
 mainSHA:=strings.Repeat("a",40)
 for _,tc:=range []struct{comp CompareResponse;want string;integrated int}{
  {CompareResponse{Status:"ahead",AheadBy:3,BehindBy:0},"ROOT_HAS_UNMERGED_SOURCE_COMMITS",0},
  {CompareResponse{Status:"behind",AheadBy:0,BehindBy:10},"SOURCE_HEAD_REACHABLE_FROM_MAIN_REVIEW_ONLY",1},
  {CompareResponse{Status:"diverged",AheadBy:3,BehindBy:10},"ROOT_HISTORY_DIVERGED_REVIEW",0},
 }{
  got,err:=inspectRootTips(context.Background(),s,w,mainSHA,
   func(_ context.Context,base,head string)(CompareResponse,error){
    if base!=mainSHA||head!=strings.Repeat("f",40){t.Fatal("bad sha");}
    return tc.comp,nil
   })
  if err!=nil{t.Fatal(err)}
  if got.RootTipsChecked!=1||got.RootCount!=2||got.Mutations!=0||got.OwnerApproval||
     got.IntegratedAncestors!=tc.integrated||got.Tips[0].Status!=tc.want||
     got.Tips[0].Action!="RETAIN_UNMERGED_UNTIL_EXACT_OWNER_AND_RIGHTS_REVIEW"{
   t.Fatalf("unapproved closure from mere source reachability: %#v",got)
  }
  if !strings.Contains(got.Markdown(),"mutations: **0**"){t.Fatal("misleading report")}
 }
}
func TestRootTipRemoteFailureAndSnapshotDeny(t *testing.T){
 s:=rootFixture();w,e:=buildWorkset(s);if e!=nil{t.Fatal(e)}
 _,err:=inspectRootTips(context.Background(),s,w,"short",
  func(context.Context,string,string)(CompareResponse,error){
   return CompareResponse{Status:"ahead",AheadBy:1},nil
  })
 if err==nil{t.Fatal("invalid main sha accepted")}
 s.Complete=false
 _,err=inspectRootTips(context.Background(),s,w,strings.Repeat("a",40),
  func(context.Context,string,string)(CompareResponse,error){
   return CompareResponse{},errors.New("upstream unavailable")
  })
 if err==nil{t.Fatal("partial source accepted")}
 s.Complete=true
 s.PRs=append(s.PRs,Pull{Number:2,Title:"root",State:"open",Draft:true,
  UpdatedAt:time.Date(2026,11,5,0,0,0,0,time.UTC),
  Head:CommitRef{Ref:"independent",SHA:strings.Repeat("f",40)},
  Base:CommitRef{Ref:"main",SHA:strings.Repeat("e",40)}})
 w,e=buildWorkset(s);if e!=nil{t.Fatal(e)}
 _,err=inspectRootTips(context.Background(),s,w,strings.Repeat("a",40),
  func(context.Context,string,string)(CompareResponse,error){
   return CompareResponse{},errors.New("upstream unavailable")
  })
 if err==nil{t.Fatal("API failure accepted")}
}
func TestRootTipNoIndependentRoot(t *testing.T){
 s:=rootFixture();w,e:=buildWorkset(s);if e!=nil{t.Fatal(e)}
 n:=0
 out,err:=inspectRootTips(context.Background(),s,w,strings.Repeat("a",40),
  func(context.Context,string,string)(CompareResponse,error){
   n++;return CompareResponse{},errors.New("should not have called")
  })
 if err!=nil||n!=0||out.RootTipsChecked!=0||out.RootCount!=1 {t.Fatal(out,err)}
}
