package sceneadapter
import (
 "math"
 "strings"
 "testing"
 "example.invalid/spatial-contract/attenuation"
)
func base()Scene{return Scene{
 SourceID:"emitter_a",ListenerID:"listener_b",Rights:OriginalRights,
 OriginalSourceSHA256:strings.Repeat("a",64),RateHz:48000,StartFrame:123,
 FrameCount:1024,Emitter:Position{East:20},Listener:Position{},
 Layout:Surround51,Envelope:attenuation.Envelope{Curve:attenuation.InverseDistance,ReferenceMeters:10,MinimumMeters:1},
}}
func TestDeterministicAndDistinctRenderIdentity(t *testing.T){
 s:=base()
 a,err:=Plan(s);if err!=nil{t.Fatal(err)}
 b,err:=Plan(s);if err!=nil||a.RenderID!=b.RenderID{t.Fatal("not deterministic")}
 if a.DistanceMeters!=20||a.Gain!=.5||len(a.ChannelLabels)!=6||a.ChannelLabels[3]!="LFE"{t.Fatalf("wrong contract %+v",a)}
 s.StartFrame++
 c,err:=Plan(s);if err!=nil||c.RenderID==a.RenderID{t.Fatal("clock identity not observed")}
 s=base();s.Listener.East=5
 c,err=Plan(s);if err!=nil||c.RenderID==a.RenderID{t.Fatal("listener identity not observed")}
}
func TestSceneNegatives(t *testing.T){
 checks:=[]func(*Scene){
  func(s *Scene){s.SourceID=""},func(s *Scene){s.SourceID=s.ListenerID},
  func(s *Scene){s.Rights="PRIVATE"},func(s *Scene){s.OriginalSourceSHA256=strings.Repeat("g",64)},
  func(s *Scene){s.OriginalSourceSHA256="0"},
  func(s *Scene){s.RateHz=44100},func(s *Scene){s.StartFrame=-1},
  func(s *Scene){s.FrameCount=-1},func(s *Scene){s.FrameCount=48000*11},
  func(s *Scene){s.Layout="7.1.4"},func(s *Scene){s.Emitter.East=math.Inf(1)},
  func(s *Scene){s.Listener.Up=math.NaN()},
  func(s *Scene){s.Emitter=Position{}},func(s *Scene){s.Envelope.MinimumMeters=0},
 }
 for i,change:=range checks{s:=base();change(&s);if _,err:=Plan(s);err==nil{t.Fatalf("accepted negative %d",i)}}
}
func TestSourceNeverMutatedAndBadPCM(t *testing.T){
 for _,layout:=range []ChannelLayout{Stereo,Surround51,Surround71}{
  s:=base();s.Layout=layout;n:=layout.Channels()
  src:=make([]float32,s.FrameCount*n)
  for i:=range src{if n>=6&&i%n==3{continue};src[i]=.2}
  out,p,err:=Apply(s,src);if err!=nil{t.Fatal(err)}
  if p.Gain!=.5||out[0]!=(float32(.2)*.5){t.Fatal("wrong amplitude")}
  if src[0]!=.2{t.Fatal("source was clobbered")}
  if n>=6 && out[3]!=0{t.Fatal("LFE leak")}
  _,_,err=Apply(s,src[:len(src)-1]);if err==nil{t.Fatal("accepted incomplete frame")}
  src[0]=float32(math.NaN());_,_,err=Apply(s,src);if err==nil{t.Fatal("accepted NaN")}
 }
}
