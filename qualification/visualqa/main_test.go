package main
import ("crypto/sha256";"encoding/hex";"math";"testing")
func positive() (Input,[]byte) {
 src:=[]byte("original synthetic BLEND source")
 sha:=sha256.Sum256(src)
 legs:=[]Spec{{Actor:"One",Leg:"Left",Pole:V{0,1,0},Upper:1.059481,Lower:1.059481},
 {Actor:"One",Leg:"Right",Pole:V{0,1,0},Upper:1.059481,Lower:1.059481}}
 frame:=func(tick int64) Frame{return Frame{Tick:tick,Poses:[]Pose{
  {Actor:"One",Leg:"Left",Hip:V{-.2,0,2},Knee:V{-.2,.35,1},Ankle:V{-.2,0,0}},
  {Actor:"One",Leg:"Right",Hip:V{.2,0,2},Knee:V{.2,.35,1},Ankle:V{.2,0,0}},
 }}}
 return Input{Schema:"scp.visualqa.l2_knee_input.v1",Rights:"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
 SourceSHA256:hex.EncodeToString(sha[:]),Legs:legs,Frames:[]Frame{frame(0),frame(12)}},src
}
func TestBendingAcceptedOnlyGeometry(t *testing.T) {
 in,src:=positive();got:=evaluate(in,src)
 if got.Status!="PASS_L2_REST_POLE_GEOMETRY_ONLY"||got.ValidBentSamples!=4||!got.VerifiedSourceBytes {t.Fatalf("%+v",got)}
}
func TestReversedKneeMustFail(t *testing.T) {
 in,src:=positive()
 in.Frames[1].Poses[0].Knee=V{-.2,-.35,1}
 got:=evaluate(in,src)
 if got.Status!="FAIL" {t.Fatalf("backwards knee incorrectly passed: %+v",got)}
 found:=false;for _,e:=range got.Findings{if e.Reason=="BACKWARD_OR_WRONG_POLE_KNEE_BEND"{found=true}}
 if !found {t.Fatalf("wrong reason: %+v",got)}
}
func TestNoIndependentPoleAbstains(t *testing.T) {
 in,src:=positive();in.Legs[0].Pole=V{0,0,1}
 got:=evaluate(in,src)
 if got.Status!="UNKNOWN" {t.Fatalf("parallel pole MUST UNKNOWN: %+v",got)}
}
func TestStraightCannotPass(t *testing.T) {
 in,src:=positive()
 for k:=range in.Frames {for j:=range in.Frames[k].Poses {
  in.Frames[k].Poses[j].Knee[1]=0
  in.Legs[j].Upper=1
  in.Legs[j].Lower=1
 }}
 got:=evaluate(in,src)
 if got.Status!="UNKNOWN" {t.Fatalf("straight-only MUST UNKNOWN: %+v",got)}
}
func TestSourceAndClockTamperingMustFail(t *testing.T) {
 in,src:=positive()
 if g:=evaluate(in,[]byte("different"));g.Status!="FAIL" {t.Fatalf("wrong source passed: %+v",g)}
 in.Frames[1].Tick=in.Frames[0].Tick
 if g:=evaluate(in,src);g.Status!="FAIL" {t.Fatalf("duplicate timestamp passed: %+v",g)}
}
func TestMissingLegAndRightsMustFail(t *testing.T) {
 in,src:=positive()
 in.Frames[1].Poses=in.Frames[1].Poses[:1]
 if g:=evaluate(in,src);g.Status!="FAIL" {t.Fatalf("missing leg passed: %+v",g)}
 in,src=positive();in.Rights="UNLICENSED"
 if g:=evaluate(in,src);g.Status!="FAIL" {t.Fatalf("rights passed: %+v",g)}
}
func TestNonFiniteMustFail(t *testing.T) {
 in,src:=positive();in.Frames[1].Poses[0].Knee[0]=math.Inf(1)
 if g:=evaluate(in,src);g.Status!="FAIL" {t.Fatalf("nonfinite passed: %+v",g)}
}
