package editable

import (
 "bytes"
 "encoding/json"
 "math/big"
 "testing"
)
func eightBar(t *testing.T)(Project,ScoreRequest){
 t.Helper()
 p:=Default();p.Beats=32 // eight original synthetic 4/4 bars
 tempo:=[]TempoPoint{{0,120},{16*PPQ,90}}
 events:=[]ChoreographyEvent{
  {ID:"intro",ActorID:"actor-a",Role:"leader",Action:"step",Tick:0},
  {ID:"offbeat",ActorID:"actor-b",Role:"follower",Action:"cross",Tick:PPQ/2},
  {ID:"bar5",ActorID:"actor-a",Role:"leader",Action:"turn",Tick:16*PPQ},
  {ID:"bar5beat2",ActorID:"actor-b",Role:"follower",Action:"clap",Tick:17*PPQ},
  {ID:"end",ActorID:"actor-a",Role:"leader",Action:"hold",Tick:32*PPQ},
 }
 r,e:=FormatScoreRequest(p,tempo,events);if e!=nil{t.Fatal(e)}
 return p,r
}
func TestEightBarTwoActorExactClock(t *testing.T){
 p,r:=eightBar(t)
 a,e:=AlignOriginalSynthetic(p,r);if e!=nil{t.Fatal(e)}
 if len(a.Events)!=5||!TimeMapIsNotPerformanceProof(a){t.Fatalf("incorrect claims %+v",a)}
 want:=[]string{"0","12000","384000","416000","896000"} // exact 48k sample clock at 120 -> 90 BPM
 for i,v:=range want{if a.Events[i].ExactSamplePosition!=v{t.Fatalf("event %d sample %s != %s",i,a.Events[i].ExactSamplePosition,v)}}
 if _,ok:=new(big.Rat).SetString(a.Events[3].ExactSeconds);!ok{t.Fatal("seconds not rational")}
 b,_:=json.Marshal(a)
 r.Events[0],r.Events[4]=r.Events[4],r.Events[0]
 c,e:=AlignOriginalSynthetic(p,r);if e!=nil{t.Fatal(e)}
 d,_:=json.Marshal(c);if !bytes.Equal(b,d){t.Fatal("same input multiset changed content id or order")}
 p2:=p;p2.Notes=append([]Note(nil),p.Notes...);p2.Notes[0].Pitch=61
 if _,e:=AlignOriginalSynthetic(p2,r);e==nil{t.Fatal("swapped source accepted")}
}
func TestFailClosedScoreErrors(t *testing.T){
 p,original:=eightBar(t)
 tests:=[]func(*ScoreRequest){
  func(r *ScoreRequest){r.Origin="PRIVATE"},
  func(r *ScoreRequest){r.AudioProjectSHA256="bad"},
  func(r *ScoreRequest){r.Schema="bad"},
  func(r *ScoreRequest){r.Tempo[0].BPM=110},
  func(r *ScoreRequest){r.Tempo[1].AtTick=0},
  func(r *ScoreRequest){r.Tempo[1].BPM=0},
  func(r *ScoreRequest){r.Events[0].ID=r.Events[1].ID},
  func(r *ScoreRequest){r.Events[0].Tick=-1},
  func(r *ScoreRequest){r.Events[0].ActorID="real-person"},
  func(r *ScoreRequest){r.Events[0].Action="contact-force"},
 }
 for i,mutate:=range tests{
  q:=original;q.Tempo=append([]TempoPoint(nil),original.Tempo...);q.Events=append([]ChoreographyEvent(nil),original.Events...);mutate(&q)
  if _,err:=AlignOriginalSynthetic(p,q);err==nil{t.Fatalf("invalid case %d accepted",i)}
 }
 if _,err:=ExactSecondsAt(-1,original.Tempo);err==nil{t.Fatal("negative tick accepted")}
}
func TestUnsupportedMeterNotSilentlyAccepted(t *testing.T){
 p,r:=eightBar(t)
 o,e:=AlignOriginalSynthetic(p,r);if e!=nil{t.Fatal(e)}
 if o.Meter!="4/4_SOURCE_PROJECT_ONLY"{t.Fatal("fake general meter support")}
 if o.AudioVerification=="VERIFIED_AUDIO"{t.Fatal("fabricated audio acceptance")}
}
