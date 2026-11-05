package main

import (
 "strings"
 "testing"
 "time"
)
func rootFixture()Snapshot{
 d:=time.Date(2026,11,5,0,0,0,0,time.UTC)
 x:=func(n int,title,head,headSHA,base,baseSHA string)Pull{
  return Pull{Number:n,Title:title,State:"open",Draft:true,Head:CommitRef{Ref:head,SHA:headSHA},Base:CommitRef{Ref:base,SHA:baseSHA},UpdatedAt:d}
 }
 a:=strings.Repeat("a",40)
 b:=strings.Repeat("b",40)
 c:=strings.Repeat("c",40)
 dsha:=strings.Repeat("d",40)
 e:=strings.Repeat("e",40)
 return Snapshot{Schema:schema,Repo:allowedRepo,AsOf:"2026-11-06",Complete:true,FetchPages:1,PRs:[]Pull{
  x(271,"original","source",a,"main",e),
  x(291,"humanized","human",b,"source",a),
  x(292,"wardrobe","wardrobe",c,"human",b),
  x(308,"parametric","parametric",dsha,"wardrobe",c),
 }}
}
func TestRootGraphPrioritizationAndEvidence(t *testing.T){
 s:=rootFixture()
 w,err:=buildWorkset(s);if err!=nil{t.Fatal(err)}
 if w.RootCount!=1||w.StackedCount!=3||w.TotalOpen!=4||w.Mutations!=0{t.Fatalf("%+v",w)}
 if len(w.Groups)!=1||w.Groups[0].RootPR!=271||w.Groups[0].MaxDepth!=3||w.Groups[0].TotalDescendants!=3||w.Groups[0].DirectChildren!=1{t.Fatal(w.Groups)}
 if !strings.Contains(w.Markdown(),"#271")||!strings.Contains(string(w.JSON()),"RETAIN_AND_REVIEW_WITH_OWNER_GATES"){t.Fatal("missing explicit hold")}
}
func TestMissingParentReject(t *testing.T){
 s:=rootFixture()
 s.PRs[1].Base.Ref="missing"
 if _,err:=buildWorkset(s);err==nil{t.Fatal("missing parent accepted")}
}
func TestParentHeadDriftReject(t *testing.T){
 s:=rootFixture()
 s.PRs[2].Base.SHA=strings.Repeat("f",40)
 if _,err:=buildWorkset(s);err==nil{t.Fatal("source SHA drift accepted")}
}
func TestDependencyCycleAndIncompleteReject(t *testing.T){
 s:=rootFixture()
 s.PRs[0].Base.Ref=s.PRs[3].Head.Ref
 s.PRs[0].Base.SHA=s.PRs[3].Head.SHA
 if _,err:=buildWorkset(s);err==nil{t.Fatal("cycle accepted")}
 s=rootFixture();s.Complete=false
 if _,err:=buildWorkset(s);err==nil{t.Fatal("partial data accepted")}
}
func TestRootsSortedByDescendantImpact(t *testing.T){
 s:=rootFixture()
 s.PRs=append(s.PRs,Pull{
  Number:2,Title:"unrelated main",State:"open",Draft:true,
  UpdatedAt:time.Date(2026,11,5,0,0,0,0,time.UTC),
  Head:CommitRef{Ref:"other",SHA:strings.Repeat("f",40)},
  Base:CommitRef{Ref:"main",SHA:strings.Repeat("e",40)},
 })
 w,err:=buildWorkset(s);if err!=nil{t.Fatal(err)}
 if w.RootCount!=2||w.Groups[0].RootPR!=271||w.Groups[1].RootPR!=2{t.Fatal(w)}
}
