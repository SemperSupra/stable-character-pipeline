package audio
import (
 "bytes"
 "encoding/json"
 "testing"
)
func fixture(surface string)Input{
 return Input{Schema:Schema,Basis:"SYNTHETIC_PLANNED",ActorID:"pony-black",Gait:"walk",
 FPS:24,SampleRate:Rate,FramesPerCycle:24,Cycles:1,
 Evaluation:"PLANNED_ONLY_NOT_EVALUATED_HOOF_CONTACT",
 Events:[]Event{
 {ActorID:"pony-black",Gait:"walk",Foot:"HL",Kind:"hoof_impact",ContactState:"planned_contact",Surface:surface,Frame:0,Sample:0,Source:"SYNTHETIC_PLANNED"},
 {ActorID:"pony-black",Gait:"walk",Foot:"FL",Kind:"hoof_impact",ContactState:"planned_contact",Surface:surface,Frame:6,Sample:12000,Source:"SYNTHETIC_PLANNED"},
 {ActorID:"pony-black",Gait:"walk",Foot:"HR",Kind:"hoof_impact",ContactState:"planned_contact",Surface:surface,Frame:12,Sample:24000,Source:"SYNTHETIC_PLANNED"},
 {ActorID:"pony-black",Gait:"walk",Foot:"FR",Kind:"hoof_impact",ContactState:"planned_contact",Surface:surface,Frame:18,Sample:36000,Source:"SYNTHETIC_PLANNED"},
 }}
}
func TestDeterministicFoley(t *testing.T){
 a,ra,e:=Render(fixture("sand"),2)
 if e!=nil{t.Fatal(e)}
 b,rb,e:=Render(fixture("sand"),2)
 if e!=nil{t.Fatal(e)}
 if !bytes.Equal(a,b)||ra.WavSha256!=rb.WavSha256{t.Fatal("non deterministic foley")}
 if len(a)!=44+2*Rate*2||ra.NonzeroSamples==0||ra.EventCount!=4{t.Fatal("empty or invalid WAV")}
 if string(a[:4])!="RIFF"||string(a[8:12])!="WAVE"{t.Fatal("not WAV")}
 s,_,e:=Render(fixture("stone"),2);if e!=nil{t.Fatal(e)}
 if bytes.Equal(a,s){t.Fatal("terrain has no effect")}
}
func TestStrictRejects(t *testing.T){
 for _,alter:=range []func(*Input){
  func(i *Input){i.Schema="wrong"},
  func(i *Input){i.Basis="PHYSICAL_VERIFIED"},
  func(i *Input){i.Evaluation="EVALUATED"},
  func(i *Input){i.Events[0].Sample=10},
  func(i *Input){i.Events[0].Surface="wood"},
  func(i *Input){i.Events[0].Foot="hoof"},
  func(i *Input){i.Events=append(i.Events,i.Events[0])},
  func(i *Input){i.Events[2].ActorID="other"},
 }{
  x:=fixture("sand")
  alter(&x)
  b,_:=json.Marshal(x)
  if _,e:=Parse(b);e==nil{t.Fatalf("accepted bad input %s",b)}
 }
}
func TestNoVocalClaims(t *testing.T){
 in:=fixture("sand")
 in.Events[0].Kind="whinny"
 raw,_:=json.Marshal(in)
 if _,e:=Parse(raw);e==nil{t.Fatal("unsupported voice accepted")}
}
