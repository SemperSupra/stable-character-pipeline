package main

import (
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func write(t *testing.T,d,n,s string)string{
 t.Helper()
 p:=filepath.Join(d,n)
 if e:=os.WriteFile(p,[]byte(s),0600);e!=nil{t.Fatal(e)}
 return p
}
func fixture(t *testing.T)[]string{
 t.Helper()
 d:=t.TempDir()
 return []string{
  write(t,d,"isa_parts_list_e.txt","concept id\trepresentation id\ten\nFMA1\tBP1\tskin\nFMA2\tBP2\theart\n"),
  write(t,d,"partof_parts_list_e.txt","concept id\trepresentation id\ten\nFMA1\tBP12\tskin\nFMA2\tBP2\theart\n"),
  write(t,d,"isa_inclusion_relation_list.txt","parent id\tparent name\tchild id\tchild name\nFMA1\tskin\tFMA2\theart\n"),
  write(t,d,"partof_inclusion_relation_list.txt","parent id\tparent name\tchild id\tchild name\nFMA1\tskin\tFMA2\theart\n"),
 }
}
func TestSourceAuditorNormalAndDistinctOntologies(t *testing.T){
 r,e:=audit(fixture(t));if e!=nil{t.Fatal(e)}
 if r.SharedConcepts!=2||r.DifferentRepresentationForSharedConcept!=1||r.ISARows!=2{t.Fatalf("%+v",r)}
 if r.ISACycles!=0||r.PartOfCycles!=0||r.Status!="SOURCE_METADATA_INSPECTED_NOT_GEOMETRY_QUALIFIED"{t.Fatalf("%+v",r)}
 if len(r.ImportantSourceConcepts["skin"])!=1{t.Fatal("concept source anchor missing")}
}
func TestRejectMalformedAndConflictingSource(t *testing.T){
 for _,test:=range []struct{name,content string}{
  {"duplicate-other-mesh","concept id\trepresentation id\ten\nFMA1\tBP1\tskin\nFMA1\tBP9\tskin\n"},
  {"wrong-columns","concept id\trepresentation id\ten\nFMA1\tskin\n"},
  {"bad-id","concept id\trepresentation id\ten\nFMAI\tBP1\tskin\n"},
  {"wrong-header","id\trepresentation id\ten\nFMA1\tBP1\tskin\n"},
  {"empty","concept id\trepresentation id\ten\n"},
 }{
  t.Run(test.name,func(t *testing.T){
   paths:=fixture(t)
   if e:=os.WriteFile(paths[0],[]byte(test.content),0600);e!=nil{t.Fatal(e)}
   if _,e:=audit(paths);e==nil{t.Fatal("accepted malformed source")}
  })
 }
}
func TestRejectUnknownEdgeAndDetectCycles(t *testing.T){
 paths:=fixture(t)
 corrupt:="parent id\tparent name\tchild id\tchild name\nFMA1\tskin\tFMA1\tskin\n"
 if e:=os.WriteFile(paths[2],[]byte(corrupt),0600);e!=nil{t.Fatal(e)}
 if _,e:=audit(paths);e==nil{t.Fatal("accepted self loop")}
 paths=fixture(t)
 cycle:="parent id\tparent name\tchild id\tchild name\nFMA1\tskin\tFMA2\theart\nFMA2\theart\tFMA1\tskin\n"
 if e:=os.WriteFile(paths[2],[]byte(cycle),0600);e!=nil{t.Fatal(e)}
 r,e:=audit(paths);if e!=nil{t.Fatal(e)}
 if r.ISACycles!=1||!strings.HasPrefix(r.Status,"HOLD"){t.Fatalf("%+v",r)}
}
