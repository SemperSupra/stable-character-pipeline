package main

import "testing"
func sample() Source {
 s:=Source{Schema:schema,Rights:rights,Scenario:"ORIGINAL_2ACTOR_WORLD_X_APPROACH_NOT_HUMAN_GAIT",Profile:"forward",FPSNum:12,FPSDen:1}
 for ai,name:=range []string{"CobaltOriginal","MarigoldOriginal"} {
  a:=Actor{ID:name}
  for i:=0;i<24;i++ {
   x:=-1.65+0.014*float64(i);if ai==1 {x=1.65-0.014*float64(i)}
   f:=Frame{Index:i,TimeNum:i,TimeDen:12,RootX:x}
   for _,id:=range []string{"Left","Right"} {
    f.Legs=append(f.Legs,Leg{ID:id,State:"stance",Hip:[]float64{x,0,1.08},Knee:[]float64{x,0,.5},Ankle:[]float64{0,0,0},Heel:[]float64{0,0,0},Toe:[]float64{0,0,0},Anchor:[]float64{0,0,0}})
   }
   a.Frames=append(a.Frames,f)
  }
  s.Actors=append(s.Actors,a)
 }
 return s
}
func TestCleanSyntheticSourceAbstainsFromHumanPass(t *testing.T) {
 r:=Evaluate(sample(),"fixture")
 if r.SourceIntegrity!="PASS_SOURCE_CONTRACT_KINEMATIC_ONLY"||r.SourceBehavior!="ABSTAIN_INSUFFICIENT_ANATOMICAL_INPUT"||r.HumanGait[:7]!="ABSTAIN" {t.Fatalf("%+v",r)}
}
func TestHostileFirstFailures(t *testing.T) {
 tests:=[]struct{name,code string;mut func(*Source)}{
  {"swapped_lr","W8_SWAPPED_LEFT_RIGHT",func(s *Source){s.Actors[0].Frames[8].Legs[0].ID="Right"}},
  {"slipping_sole","W8_STANCE_SLIP_OR_FALSE_CONTACT",func(s *Source){s.Actors[0].Frames[8].Legs[0].Ankle[0]=0.07}},
  {"penetration","W8_GROUND_PENETRATION",func(s *Source){s.Actors[0].Frames[8].Legs[0].Toe[2]=-.10}},
  {"bad_clock","W8_CLOCK_OR_ROOT_NONFINITE",func(s *Source){s.Actors[0].Frames[8].TimeNum=9}},
  {"wrong_rights","W8_SOURCE_ID_RIGHTS_CLOCK",func(s *Source){s.Rights="UNVERIFIED"}},
  {"root_reversal","W8_REVERSED_OR_DISCONTINUOUS_ACTION_DIRECTION",func(s *Source){s.Actors[0].Frames[9].RootX=-4}},
  {"actor_cross","W8_ACTOR_ROOT_ORDER_CROSSED",func(s *Source){s.Actors[0].Frames[23].RootX=2.0}},
 }
 for _,tt:=range tests {
  t.Run(tt.name,func(t *testing.T){
   s:=sample();tt.mut(&s);r:=Evaluate(s,"hostile")
   if r.SourceIntegrity!="FAIL" {t.Fatalf("false-pass: %+v",r)}
   found:=false;for _,f:=range r.Findings{if f.Code==tt.code&&f.Status=="FAIL"{found=true}}
   if !found {t.Fatalf("missing first failure %s: %+v",tt.code,r.Findings)}
  })
 }
}
