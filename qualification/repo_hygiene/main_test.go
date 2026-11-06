package main

import (
 "strings"
 "testing"
 "time"
)

func base() Snapshot {
 return Snapshot{Schema:schema,Repo:allowedRepo,AsOf:"2026-11-06",Complete:true,FetchPages:1,PRs:[]Pull{
  {Number:292,Title:"modular parent",State:"open",Draft:true,Head:CommitRef{Ref:"wardrobe",SHA:strings.Repeat("a",40)},Base:CommitRef{Ref:"human",SHA:strings.Repeat("b",40)},UpdatedAt:time.Date(2026,11,5,0,0,0,0,time.UTC)},
  {Number:308,Title:"parametric child",State:"open",Draft:true,Head:CommitRef{Ref:"parametric",SHA:strings.Repeat("c",40)},Base:CommitRef{Ref:"wardrobe",SHA:strings.Repeat("a",40)},UpdatedAt:time.Date(2026,11,5,0,0,0,0,time.UTC)},
 }}
}
func TestReadOnlyAuditStacked(t *testing.T){
 a:=base();r,e:=audit(a,14);if e!=nil{t.Fatal(e)}
 if r.Mutations!=0||r.PRsScanned!=2||r.Findings[0].Number!=308||r.Findings[0].Action!="RETAIN_AND_REVIEW"{t.Fatal(r)}
 if !strings.Contains(strings.Join(r.Findings[0].Classification,","),"OPEN_PARENT_PR_292"){t.Fatal(r.Findings[0])}
 if !strings.Contains(renderMD(r),"No merges, closes") {t.Fatal("missing safety")}
}
func TestIncompleteAlwaysHeld(t *testing.T){
 a:=base();a.Complete=false;r,e:=audit(a,14);if e!=nil{t.Fatal(e)}
 if !strings.Contains(strings.Join(r.Findings[0].Hold,","),"INCOMPLETE_SNAPSHOT") {t.Fatal(r.Findings[0])}
}
func TestOutOfScopeAndMalformedRefFail(t *testing.T){
 a:=base();a.Repo="SemperSupra/stable-character-pipeline-private";if _,e:=audit(a,14);e==nil{t.Fatal("private allowed")}
 a=base();a.PRs[0].Head.SHA="short";if _,e:=audit(a,14);e==nil{t.Fatal("bad SHA allowed")}
 a=base();a.PRs[0].HTMLURL="https://evil.test/pull/292";if _,e:=audit(a,14);e==nil{t.Fatal("foreign URL allowed")}
}
func TestNoFalseClosureOnStale(t *testing.T){
 a:=base();a.PRs[0].UpdatedAt=time.Date(2026,1,1,0,0,0,0,time.UTC);r,e:=audit(a,14);if e!=nil{t.Fatal(e)}
 for _,p:=range r.Findings{if p.Action!="RETAIN_AND_REVIEW" {t.Fatal("unsafe action",p)}}
}
func TestDuplicateHeadsNotAutoClosed(t *testing.T){
 a:=base();a.PRs[1].Head.SHA=a.PRs[0].Head.SHA;r,e:=audit(a,14);if e!=nil{t.Fatal(e)}
 for _,p:=range r.Findings {if !strings.Contains(strings.Join(p.Classification,","),"SHARED_HEAD_COMMIT_REVIEW")||p.Action!="RETAIN_AND_REVIEW"{t.Fatal(p)}}
}
func TestRejectNonOpenMergedAndRepeated(t *testing.T){
 a:=base();a.PRs[1].State="closed";if _,e:=audit(a,14);e==nil{t.Fatal("closed row allowed")}
 a=base();a.PRs[1].Number=a.PRs[0].Number;if _,e:=audit(a,14);e==nil{t.Fatal("duplicate row allowed")}
}
func TestBadDateAndThreshold(t *testing.T){
 a:=base();a.AsOf="tomorrow";if _,e:=audit(a,14);e==nil{t.Fatal("date")}
 a=base();if _,e:=audit(a,0);e==nil{t.Fatal("threshold")}
}

func TestRejectFullLengthMalformedCommitHashes(t *testing.T) {
 for _,tc:=range []struct{name string;head bool;invalid string}{
  {"head_nonhex",true,strings.Repeat("z",40)},
  {"base_nonhex",false,strings.Repeat("z",40)},
  {"head_uppercase",true,strings.Repeat("A",40)},
  {"base_uppercase",false,strings.Repeat("A",40)},
 } {
  t.Run(tc.name,func(t *testing.T){
   a:=base()
   if tc.head {a.PRs[0].Head.SHA=tc.invalid} else {a.PRs[0].Base.SHA=tc.invalid}
   if _,err:=audit(a,14);err==nil {t.Fatal("invalid full-length SHA accepted")}
  })
 }
}
