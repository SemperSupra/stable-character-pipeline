package main

import(
 "strings"
 "testing"
 "example.invalid/spatial-contract/contract"
)
func TestSampleWindowsCross1024Boundaries(t *testing.T){
 s,_,r:=admitted(t)
 s.Emitters[1].SourceStartFrame=24*1024-1
 s.Emitters[1].SourceStopFrame=36*1024+1
 if e:=s.Validate();e!=nil{t.Fatal(e)}
 lines,_,e:=build(s,r);if e!=nil{t.Fatal(e)}
 if len(lines)!=47{t.Fatal("wrong block count")}
 for i,line:=range lines{
  fields:=strings.Fields(line)
  if len(fields)!=16{t.Fatalf("block %d fields %d",i,len(fields))}
  if fields[12]!="0"||fields[13]!="48000"||fields[14]!="24575"||fields[15]!="36865" {
   t.Fatalf("gates drift at block %d: %s",i,line)
  }
 }
}
func TestInvalidActivityWindowsFailClosed(t *testing.T){
 cases:=[]struct{name string;start,stop int}{
  {"negative start",-1,40000},
  {"start beyond scene",48000,0},
  {"stop before start",23000,22000},
  {"stop at start",24575,24575},
  {"stop past scene",24575,48001},
 }
 for _,tt:=range cases{t.Run(tt.name,func(t *testing.T){
  s,_,r:=admitted(t)
  s.Emitters[1].SourceStartFrame=tt.start;s.Emitters[1].SourceStopFrame=tt.stop
  if _,_,e:=build(s,r);e==nil{t.Fatal("bad absolute window admitted")}
 })}
}
