package main
import (
 "go/parser"
 "go/token"
 "strings"
 "testing"
)
func TestR068NormalizeGoCandidate(t *testing.T){
 nl:=string(rune(10))
 fence:="```"
 for _,tc:=range []struct{name,src,mode string;valid bool}{
  {"full","package main"+nl+"func TestR062Case() {}","NO_NORMALIZATION",true},
  {"commented","// synthetic"+nl+"package main"+nl+"func TestR062Case() {}","NO_NORMALIZATION",true},
  {"wrapper","func TestR062Case() {}","ADD_PACKAGE_ONLY",true},
  {"fenced",fence+"go"+nl+"func TestR062Case() {}"+nl+fence,"STRIP_FENCE_AND_ADD_PACKAGE",true},
  {"junk","not Go","NO_NORMALIZATION",false},
 }{
  t.Run(tc.name,func(t *testing.T){
   got,mode:=normalizeCandidateGo(tc.src)
   if mode!=tc.mode{t.Fatalf("intervention changed: %q",mode)}
   _,err:=parser.ParseFile(token.NewFileSet(),"candidate.go",got,parser.AllErrors)
   if (err==nil)!=tc.valid{t.Fatalf("expected valid=%v err=%v source=%s",tc.valid,err,got)}
   if tc.valid&&!strings.Contains(got,"func TestR062"){t.Fatal("lost test function")}
  })
 }
}
