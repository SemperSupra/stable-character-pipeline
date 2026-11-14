package bakeoffgate

import (
 "bytes"
 "encoding/json"
 "strings"
 "testing"
)

func h(s string) string{return strings.Repeat(s,64)}
func fixture() Plan {
 p:=Plan{
  Schema:Schema,Venue:"public_github_actions",Operation:"geometry_evaluation",
  NativeJointCount:127,ImportedJointCount:126,
  JointMapVerification:"INDEPENDENTLY_VERIFIED_127_TO_126",
  OutputScope:"NUMERIC_AGGREGATES_ONLY",Claim:"DIAGNOSTIC_ONLY",
  Inputs:[]Input{
   {"model","model_weights",h("a")},
   {"cmu07_01","motion",h("b")},
   {"cmu07_02","motion",h("c")},
   {"joint_map","joint_crosswalk",h("d")},
   {"topology_map","topology_crosswalk",h("e")},
   {"calibration","unit_calibration",h("f")},
   {"rest_pose","rest_pose",h("1")},
  },
 }
 engines:=[]string{"native_correctives_off","native_correctives_on","blender_linear_skinning","blender_preserve_volume"}
 for _,v:=range []struct{id string;frames int;motion string}{{"CMU07_01",64,h("b")},{"CMU07_02",66,h("c")}}{
  c:=Clip{ID:v.id,Frames:v.frames,MotionSHA256:v.motion,ModelSHA256:h("a"),
   JointMapSHA256:h("d"),TopologyMapSHA256:h("e"),CalibrationSHA256:h("f"),RestPoseSHA256:h("1")}
  p.Clips=append(p.Clips,c)
  for _,engine:=range engines{
   p.Arms=append(p.Arms,Arm{ClipID:c.ID,Engine:engine,Frames:c.Frames,
    MotionSHA256:c.MotionSHA256,ModelSHA256:c.ModelSHA256,
    JointMapSHA256:c.JointMapSHA256,TopologyMapSHA256:c.TopologyMapSHA256,
    CalibrationSHA256:c.CalibrationSHA256,RestPoseSHA256:c.RestPoseSHA256})
  }
 }
 return p
}
func registry(p Plan)Registry{
 r:=Registry{Grants:map[string]Grant{}}
 for _,in:=range p.Inputs{
  r.Grants[in.ID]=Grant{InputID:in.ID,Kind:in.Kind,SHA256:in.SHA256,
   Venue:p.Venue,Operation:p.Operation,Scope:"PUBLIC_ADMITTED",ProofSHA256:h("9")}
 }
 return r
}
func reject(t *testing.T,p Plan,r Registry){
 t.Helper();v,e:=Validate(p,r)
 if e==nil{t.Fatalf("unsafe plan accepted: %+v",v)}
 if v.Geometry!="HOLD_REAL_MHR_FULL_SEQUENCE"||v.CanonicalCharacterPack!="HOLD_OWNER_HUMAN_ONLY"{
  t.Fatalf("rejection lost HOLD: %+v",v)
 }
}
func TestSyntheticMatchedPlanStillNotQualityPass(t *testing.T){
 p:=fixture();v,e:=Validate(p,registry(p))
 if e!=nil{t.Fatal(e)}
 if v.Status!=Status||v.Geometry!="HOLD_REAL_MHR_FULL_SEQUENCE"||v.Cinematic!="HOLD_HUMAN_ANATOMY_AND_VISUAL_REVIEW"{
  t.Fatalf("false quality promotion %+v",v)
 }
}
func TestUnadmittedSourceRejected(t *testing.T){
 p:=fixture();r:=registry(p);delete(r.Grants,"model");reject(t,p,r)
}
func TestChangedModelWeightsRejected(t *testing.T){
 p:=fixture();r:=registry(p);p.Inputs[0].SHA256=h("2");reject(t,p,r)
}
func TestRestrictedSourceOnPublicRunnerRejected(t *testing.T){
 p:=fixture();r:=registry(p);g:=r.Grants["cmu07_01"];g.Scope="CONTROLLED_LOCAL";r.Grants["cmu07_01"]=g;reject(t,p,r)
}
func TestVenueGrantIsSpecific(t *testing.T){
 p:=fixture();r:=registry(p);p.Venue="private_github_actions";reject(t,p,r)
}
func TestNonCommercialDoesNotImplyAdmission(t *testing.T){
 p:=fixture();r:=registry(p);g:=r.Grants["model"];g.Scope="NON_COMMERCIAL";r.Grants["model"]=g;reject(t,p,r)
}
func TestMissingJointCrosswalkRejected(t *testing.T){
 p:=fixture();r:=registry(p);p.JointMapVerification="UNKNOWN_127_TO_126";reject(t,p,r)
}
func TestMismatchedJointPoseRejected(t *testing.T){
 p:=fixture();r:=registry(p);p.Arms[3].MotionSHA256=h("3");reject(t,p,r)
}
func TestMismatchedRestPoseRejected(t *testing.T){
 p:=fixture();r:=registry(p);p.Arms[1].RestPoseSHA256=h("4");reject(t,p,r)
}
func TestMismatchedPhysicalUnitsRejected(t *testing.T){
 p:=fixture();r:=registry(p);p.Arms[2].CalibrationSHA256=h("5");reject(t,p,r)
}
func TestUnverifiedTopologyRejected(t *testing.T){
 p:=fixture();r:=registry(p);p.Arms[0].TopologyMapSHA256=h("6");reject(t,p,r)
}
func TestChangedFrameCountRejected(t *testing.T){
 p:=fixture();r:=registry(p);p.Arms[4].Frames=65;reject(t,p,r)
}
func TestGroundSnapConfounderRejected(t *testing.T){
 p:=fixture();r:=registry(p);p.Arms[0].GroundSnap=true;reject(t,p,r)
}
func TestDuplicateEngineRejected(t *testing.T){
 p:=fixture();r:=registry(p);p.Arms[0].Engine=p.Arms[1].Engine;reject(t,p,r)
}
func TestMissingClipRejected(t *testing.T){
 p:=fixture();r:=registry(p);p.Clips=p.Clips[:1];reject(t,p,r)
}
func TestFalseCinematicClaimRejected(t *testing.T){
 p:=fixture();r:=registry(p);p.Claim="PHOTOREALISM_PASS";reject(t,p,r)
}
func TestSourceArtifactOutputRejected(t *testing.T){
 p:=fixture();r:=registry(p);p.OutputScope="NATIVE_BLEND";reject(t,p,r)
}
func TestTrustedRecordMustHaveProof(t *testing.T){
 p:=fixture();r:=registry(p);g:=r.Grants["model"];g.ProofSHA256="not-a-hash";r.Grants["model"]=g;reject(t,p,r)
}
func TestStrictJSONRejectsUnknownAndConcatenation(t *testing.T){
 p:=fixture();b,e:=json.Marshal(p);if e!=nil{t.Fatal(e)}
 decoded,e:=DecodeStrict(b);if e!=nil||len(decoded.Arms)!=8{t.Fatalf("roundtrip failure: %v",e)}
 bad:=bytes.Replace(b,[]byte(`"claim":`),[]byte(`"untrusted":"grant","claim":`),1)
 if _,e:=DecodeStrict(bad);e==nil{t.Fatal("unknown field accepted")}
 if _,e:=DecodeStrict(append(b,b...));e==nil{t.Fatal("concatenated JSON accepted")}
}
