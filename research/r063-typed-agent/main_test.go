package main

import (
 "bytes"
 "strings"
 "testing"
)

func good() proposedCases {
 return proposedCases{Cases:[]proposedCase{
  {Input:"src/good",Reject:false},
  {Input:"/absolute",Reject:true},
  {Input:"src/../invalid",Reject:true},
  {Input:"src/valid/**",Reject:false},
 }}
}

func TestR063Contract(t *testing.T) {
 if err:=validateCases(good());err!=nil{t.Fatal(err)}
 for name,mutate:=range map[string]func(*proposedCases){
  "duplicate":func(b *proposedCases){b.Cases[1].Input=b.Cases[0].Input},
  "insufficient-negative":func(b *proposedCases){for i:=range b.Cases{b.Cases[i].Reject=false}},
  "insufficient-positive":func(b *proposedCases){for i:=range b.Cases{b.Cases[i].Reject=true}},
  "oversize":func(b *proposedCases){b.Cases[0].Input=strings.Repeat("x",400)},
  "missing":func(b *proposedCases){b.Cases=b.Cases[:2]},
 }{
  t.Run(name,func(t *testing.T){
   b:=good()
   mutate(&b)
   if err:=validateCases(b);err==nil{t.Fatal("invalid model proposal accepted")}
  })
 }
}
func TestR063DeterministicSource(t *testing.T) {
 b:=good()
 for _,lane:=range []string{"path","json"}{
  first,err:=renderTest(lane,"m15",b)
  if err!=nil{t.Fatal(lane,err)}
  second,err:=renderTest(lane,"m15",b)
  if err!=nil{t.Fatal(lane,err)}
  if !bytes.Equal(first,second){t.Fatal("nondeterministic source",lane)}
  if !bytes.Contains(first,[]byte("TestR063M15")){t.Fatal("test discovery missing",lane)}
 }
 if _,err:=renderTest("unknown","m15",b);err==nil{t.Fatal("unknown lane generated")}
}
func TestR063ModelsAndPrompts(t *testing.T) {
 for _,model:=range []string{"qwen2.5-coder:1.5b","qwen2.5-coder:3b"}{
  if _,err:=modelTag(model);err!=nil{t.Fatal(err)}
 }
 if _,err:=modelTag("anything-else");err==nil{t.Fatal("unadmitted model")}
 for _,lane:=range []string{"path","json"}{
  if p,err:=taskPrompt(lane);err!=nil||!strings.Contains(p,"cases"){t.Fatal(err)}
 }
 if _,err:=taskPrompt("production");err==nil{t.Fatal("unadmitted lane")}
}
