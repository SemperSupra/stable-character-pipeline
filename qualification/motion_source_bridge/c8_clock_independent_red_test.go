package main
import(
 "strings"
 "testing"
)
// Independent RED controls. A receipt carrying plausible samples can still lie
// about its original clock or audio project. These are NOT new motion data.
func TestReviewC8RejectSourceProjectSubstitution(t *testing.T){
 f,s:=fixture()
 s["source_audio_project_sha256"]=strings.Repeat("b",64)
 a,b:=put(f,s)
 if _,err:=bridge(a,b);err==nil {t.Fatal("RED: arbitrary 64-hex project substituted but source accepted")}
}
func TestReviewC8RejectTickToSecondsMismatch(t *testing.T){
 f,s:=fixture()
 // First phase is 120 BPM = 24000 samples/beat at 48k, 480 PPQ.
 // Claim two beats but reuse one-beat exact seconds+samples.
 s["events"].([]any)[1].(map[string]any)["tick"]=960*2
 a,b:=put(f,s)
 if _,err:=bridge(a,b);err==nil {t.Fatal("RED: forged event tick accepted despite sample/seconds agreeing with each other")}
}
func TestReviewC8RejectMissingClockIntegrityFields(t *testing.T){
 f,s:=fixture()
 // Original C5 time map emits these fields, but the bridge accepts their omission.
 delete(s,"clock_alignment_status")
 delete(s,"score_minus_audio_end_samples")
 a,b:=put(f,s)
 if _,err:=bridge(a,b);err==nil {t.Fatal("RED: omitted clock divergence evidence accepted")}
}
