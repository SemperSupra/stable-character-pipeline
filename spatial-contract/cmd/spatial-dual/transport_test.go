package main

import(
 "strings"
 "testing"
 "example.invalid/spatial-contract/contract"
)
func TestClipRelativeFrameTransport(t *testing.T){
 s,_,r:=admitted(t)
 em:=&s.Emitters[1]
 em.SourceStartFrame=24575
 em.SourceStopFrame=36865
 em.SourceTransport="clip_relative"
 em.SourceOffsetFrame=512
 if e:=s.Validate();e!=nil{t.Fatal(e)}
 test:=[]struct{frame,index int;active bool}{
  {24574,-1,false},
  {24575,512,true},
  {24576,513,true},
  {36864,12801,true},
  {36865,-1,false},
 }
 for _,tt:=range test{
  index,active,e:=contract.SourceFrameAt(*em,tt.frame,48000)
  if e!=nil||active!=tt.active||index!=tt.index{
   t.Fatalf("at %d source index=%d active=%t want index=%d active=%t err=%v",tt.frame,index,active,tt.index,tt.active,e)
  }
 }
 lines,_,e:=build(s,r);if e!=nil{t.Fatal(e)}
 if len(lines)!=47{t.Fatal("lost native blocks")}
 for i,line:=range lines{
  fields:=strings.Fields(line)
  if len(fields)!=20{t.Fatalf("block %d wanted transport extension, got %d",i,len(fields))}
  if strings.Join(fields[16:]," ")!="scene_locked 0 clip_relative 512"{
   t.Fatalf("unexpected transport extension in block %d: %v",i,fields[16:])
  }
 }
}
func TestLegacySceneLockedIsUnchanged(t *testing.T){
 s,_,r:=admitted(t)
 s.Emitters[1].SourceStartFrame=24575
 s.Emitters[1].SourceStopFrame=36865
 lines,_,e:=build(s,r);if e!=nil{t.Fatal(e)}
 for _,line:=range lines{
  if len(strings.Fields(line))!=16{t.Fatal("legacy W3b blockplan was changed")}
 }
 i,ok,e:=contract.SourceFrameAt(s.Emitters[1],24575,48000)
 if e!=nil||!ok||i!=24575{t.Fatalf("legacy source lock drift: %d %t %v",i,ok,e)}
}
func TestRejectUnsafeFileTransport(t *testing.T){
 cases:=[]struct{name,mode string;offset,start,stop int}{
  {"unsupported mode","file_loop",0,24575,36865},
  {"offset without mode","",512,24575,36865},
  {"negative offset","clip_relative",-1,24575,36865},
  {"source overrun","clip_relative",44000,24575,36865},
  {"window inversion","clip_relative",512,37000,36000},
  {"source initial past end","clip_relative",48000,24575,36865},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){
  s,_,r:=admitted(t)
  em:=&s.Emitters[1];em.SourceStartFrame=tc.start;em.SourceStopFrame=tc.stop
  em.SourceTransport=tc.mode;em.SourceOffsetFrame=tc.offset
  if _,_,e:=build(s,r);e==nil{t.Fatal("unsafe source-file transport admitted")}
 })}
}
