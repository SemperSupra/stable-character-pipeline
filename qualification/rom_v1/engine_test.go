package main
import (
 "crypto/sha256"
 "encoding/hex"
 "math"
 "reflect"
 "strings"
 "testing"
)
func p(x float64)*float64{return &x}
func fixture()(Input,[]byte){
 src:=[]byte("original synthetic range of motion fixture");h:=sha256.Sum256(src)
 joints:=[]Joint{}
 for _,id:=range []string{"limb_hinge","linked_hinge"}{
  joints=append(joints,Joint{ID:id,Kind:"revolute",Unit:"rad",Frame:"PARENT_LOCAL_TEST_ONLY",Provenance:"SYNTHETIC_TEST_ONLY",
   Min:p(-1),Max:p(1),SoftMin:p(-.8),SoftMax:p(.8),Velocity:p(1),Acceleration:p(10),Jerk:p(60)})
 }
 frames:=[]Frame{}
 for i,q:=range []float64{0,.04,.08,.10,.12}{
  frames=append(frames,Frame{Tick:int64(i),Q:map[string]float64{"limb_hinge":q,"linked_hinge":-q}})
 }
 return Input{Schema:"scp.rom.v1_input",Rights:"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
  SourceSHA256:hex.EncodeToString(h[:]),Morphology:"synthetic_fixture",Context:"fictional_unloaded",
  RateNum:12,RateDen:1,Joints:joints,Frames:frames,
  Couplings:[]Coupling{{Master:"limb_hinge",Slave:"linked_hinge",Multiplier:-1,Tolerance:.001,Provenance:"SYNTHETIC_TEST_ONLY"}}},src
}
func has(r Result,code string)bool{for _,x:=range r.Findings{if x.Code==code{return true}};return false}
func TestValidFictionalFixtureNeverAnatomical(t *testing.T){
 in,src:=fixture();r:=evaluate(in,src)
 if r.Status!="PASS_SYNTHETIC_SCALAR_LIMITS_ONLY"||r.AnatomyAcceptance!="NOT_QUALIFIED"||!r.VerifiedSourceBytes{t.Fatalf("%+v",r)}
}
func TestHardROM(t *testing.T){
 in,src:=fixture();in.Frames[2].Q["limb_hinge"]=1.2
 if r:=evaluate(in,src);r.Status!="FAIL"||!has(r,"HARD_ROM_VIOLATION"){t.Fatalf("%+v",r)}
}
func TestVelocityWithinHardROM(t *testing.T){
 in,src:=fixture();in.Frames[1].Q["limb_hinge"]=.5
 if r:=evaluate(in,src);r.Status!="FAIL"||!has(r,"VELOCITY_LIMIT"){t.Fatalf("%+v",r)}
}
func TestAcceleration(t *testing.T){
 in,src:=fixture()
 for i:=range in.Joints{in.Joints[i].Acceleration=p(2);in.Joints[i].Jerk=p(10000);in.Joints[i].Velocity=p(100)}
 if r:=evaluate(in,src);r.Status!="FAIL"||!has(r,"ACCELERATION_LIMIT"){t.Fatalf("%+v",r)}
}
func TestJerk(t *testing.T){
 in,src:=fixture()
 for i:=range in.Joints{in.Joints[i].Jerk=p(5)}
 if r:=evaluate(in,src);r.Status!="FAIL"||!has(r,"JERK_LIMIT"){t.Fatalf("%+v",r)}
}
func TestCrossJointCoupling(t *testing.T){
 in,src:=fixture();in.Frames[2].Q["linked_hinge"]=.08
 if r:=evaluate(in,src);r.Status!="FAIL"||!has(r,"JOINT_COUPLING_VIOLATION"){t.Fatalf("%+v",r)}
}
func TestSoftMarginNotHardVeto(t *testing.T){
 in,src:=fixture()
 in.Frames[2].Q["limb_hinge"]=.85;in.Frames[2].Q["linked_hinge"]=-.85
 for i:=range in.Joints{in.Joints[i].Velocity=p(100);in.Joints[i].Acceleration=p(1000);in.Joints[i].Jerk=p(20000)}
 r:=evaluate(in,src)
 if r.Status!="PASS_SYNTHETIC_SCALAR_LIMITS_ONLY"||!has(r,"SOFT_MARGIN"){t.Fatalf("%+v",r)}
}
func TestRightsSHAAndUnqualifiedSpecies(t *testing.T){
 in,src:=fixture();in.SourceSHA256=strings.Repeat("0",64)
 if r:=evaluate(in,src);r.Status!="FAIL"||!has(r,"SOURCE_SHA_MISMATCH"){t.Fatalf("%+v",r)}
 in,src=fixture();in.Rights="PRIVATE_PERSON_UNAUTHORIZED"
 if r:=evaluate(in,src);r.Status!="FAIL"{t.Fatalf("%+v",r)}
 for _,kind:=range []string{"human","animal","machine","designed_other"}{
  in,src=fixture();in.Morphology=kind
  if r:=evaluate(in,src);r.Status!="UNKNOWN"||!has(r,"BIOLOGICAL_OR_MECHANISM_LIMITS_UNADMITTED"){t.Fatalf("%s: %+v",kind,r)}
 }
}
func TestMissingVelocityAndEffortAreUnknown(t *testing.T){
 in,src:=fixture();in.Joints[0].Jerk=nil
 if r:=evaluate(in,src);r.Status!="UNKNOWN"||!has(r,"DYNAMIC_ENVELOPE_INCOMPLETE"){t.Fatalf("%+v",r)}
 in,src=fixture();in.Joints[0].Effort=p(10)
 if r:=evaluate(in,src);r.Status!="UNKNOWN"||!has(r,"EFFORT_OBSERVATION_MISSING"){t.Fatalf("%+v",r)}
}
func TestMissingDOFClockFrameAndNonFiniteReject(t *testing.T){
 in,src:=fixture();delete(in.Frames[2].Q,"limb_hinge")
 if r:=evaluate(in,src);r.Status!="FAIL"{t.Fatalf("%+v",r)}
 in,src=fixture();in.Frames[2].Tick=1
 if r:=evaluate(in,src);r.Status!="FAIL"||!has(r,"CLOCK_OR_POSITION_COVERAGE"){t.Fatalf("%+v",r)}
 in,src=fixture();in.Joints[0].Frame="UNAPPROVED"
 if r:=evaluate(in,src);r.Status!="UNKNOWN"{t.Fatalf("%+v",r)}
 in,src=fixture();in.Frames[2].Q["limb_hinge"]=math.Inf(1)
 if r:=evaluate(in,src);r.Status!="FAIL"{t.Fatalf("%+v",r)}
}
func TestDecisionDeterminism(t *testing.T){
 in,src:=fixture();a:=evaluate(in,src)
 for i:=0;i<100;i++{b:=evaluate(in,src);if !reflect.DeepEqual(a,b){t.Fatalf("nondeterministic %+v %+v",a,b)}}
}
