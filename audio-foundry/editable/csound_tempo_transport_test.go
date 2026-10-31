package editable

import(
 "strings"
 "testing"
)
func TestCsoundTargetTransportHonorsOriginalSyntheticTempo(t *testing.T){
 p:=EightBarFixtureProject()
 r,e:=FormatScoreRequest(p,[]TempoPoint{{AtTick:0,BPM:120},{AtTick:16*PPQ,BPM:90}},
 []ChoreographyEvent{{ID:"a",ActorID:"actor-a",Role:"leader",Action:"step",Tick:0}})
 if e!=nil{t.Fatal(e)}
 cs,e:=CsoundTempoDiagnostic(p,r);if e!=nil{t.Fatal(e)}
 text:=string(cs)
 if strings.Count(text,"\ni 1 ")!=len(p.Notes)||!strings.Contains(text,"sr = 48000")||
 !strings.Contains(text,"ksmps = 1")||!strings.Contains(text,"i 1 8.000000000000")||
 !strings.Contains(text,"i 1 9.333333333333")||!strings.Contains(text,"f 0 18.666666666667"){
  t.Fatalf("target transport not grounded: %s",text)
 }
 r.AudioProjectSHA256="forged"
 if _,e:=CsoundTempoDiagnostic(p,r);e==nil{t.Fatal("forged source admitted")}
}
