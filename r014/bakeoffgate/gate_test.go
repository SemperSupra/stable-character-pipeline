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
   {"native_fbx","native_fbx",h("2")},
   {"corrective_activation","corrective_activation_weights",h("3")},
   {"corrective_shapes_lod1","lod1_corrective_shapes",h("4")},
   {"sampling_policy","sampling_policy",h("5")},
  },
 }
 engines:=[]string{"native_correctives_off","native_correctives_on","blender_linear_skinning","blender_preserve_volume"}
 for _,v:=range []struct{id string;frames int;motion string}{{"CMU07_01",64,h("b")},{"CMU07_02",66,h("c")}}{
  c:=Clip{ID:v.id,Frames:v.frames,MotionSHA256:v.motion,ModelSHA256:h("a"),
   JointMapSHA256:h("d"),TopologyMapSHA256:h("e"),CalibrationSHA256:h("f"),RestPoseSHA256:h("1"),
   NativeFBXSHA256:h("2"),CorrectiveActivationSHA256:h("3"),
   CorrectiveShapesSHA256:h("4"),SamplingPolicySHA256:h("5"),
   SourceSampleCount:map[string]int{"CMU07_01":316,"CMU07_02":329}[v.id],
   SourceHz:120,TargetHz:24,Stride:5,FirstSourceIndex:0,
   LastSourceIndex:map[string]int{"CMU07_01":315,"CMU07_02":325}[v.id],
   SamplingMethod:"EXACT_INTEGER_STRIDE_NO_INTERPOLATION",LOD:1}
  indices:=make([]int,c.Frames)
  for i:=range indices{indices[i]=i*c.Stride}
  c.SampleManifestSHA256=SampleManifestDigest(c.ID,c.MotionSHA256,
   c.SamplingPolicySHA256,c.SourceSampleCount,c.SourceHz,c.TargetHz,indices)
  p.Clips=append(p.Clips,c)
  for _,engine:=range engines{
   p.Arms=append(p.Arms,Arm{ClipID:c.ID,Engine:engine,Frames:c.Frames,
    MotionSHA256:c.MotionSHA256,ModelSHA256:c.ModelSHA256,
    JointMapSHA256:c.JointMapSHA256,TopologyMapSHA256:c.TopologyMapSHA256,
    CalibrationSHA256:c.CalibrationSHA256,RestPoseSHA256:c.RestPoseSHA256,
    NativeFBXSHA256:c.NativeFBXSHA256,
    CorrectiveActivationSHA256:c.CorrectiveActivationSHA256,
    CorrectiveShapesSHA256:c.CorrectiveShapesSHA256,
    SamplingPolicySHA256:c.SamplingPolicySHA256,
    SourceSampleCount:c.SourceSampleCount,SourceHz:c.SourceHz,TargetHz:c.TargetHz,
    Stride:c.Stride,FirstSourceIndex:c.FirstSourceIndex,
    LastSourceIndex:c.LastSourceIndex,SamplingMethod:c.SamplingMethod,
    SampleManifestSHA256:c.SampleManifestSHA256,
    LOD:c.LOD,ApplyCorrectives:engine=="native_correctives_on"})
  }
 }
 return p
}
func registry(p Plan)Registry{
 r:=Registry{Grants:map[string]Grant{},Samples:map[string]SamplingWitness{},
  Crosswalk:CrosswalkProof{SHA256:h("d"),NativeJoints:127,ImportedJoints:126,
   Verified:true,ProofSHA256:h("8")}}
 for _,c:=range p.Clips{
  indices:=make([]int,c.Frames)
  for i:=range indices{indices[i]=i*c.Stride}
  r.Samples[c.ID]=SamplingWitness{
   ClipID:c.ID,MotionSHA256:c.MotionSHA256,PolicySHA256:c.SamplingPolicySHA256,
   SourceFrameCount:c.SourceSampleCount,SourceHz:c.SourceHz,TargetHz:c.TargetHz,
   Indices:indices,ManifestSHA256:SampleManifestDigest(c.ID,c.MotionSHA256,
   c.SamplingPolicySHA256,c.SourceSampleCount,c.SourceHz,c.TargetHz,indices),
   Verified:true,ReviewerProofSHA256:h("9"),
  }
 }
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

func TestSelfAssertedCrosswalkWithoutTrustedAttestationRejected(t *testing.T){
 p:=fixture();r:=registry(p);r.Crosswalk.Verified=false;reject(t,p,r)
}
func TestTrustedCrosswalkWrongHashRejected(t *testing.T){
 p:=fixture();r:=registry(p);r.Crosswalk.SHA256=h("7");reject(t,p,r)
}
func TestTrustedCrosswalkWrongArityRejected(t *testing.T){
 p:=fixture();r:=registry(p);r.Crosswalk.ImportedJoints=127;reject(t,p,r)
}
func TestPrivateRunnerCannotInheritLocalGrant(t *testing.T){
 p:=fixture();p.Venue="private_github_actions";r:=registry(p)
 for id,g:=range r.Grants {g.Venue=p.Venue;g.Scope="CONTROLLED_LOCAL";r.Grants[id]=g}
 reject(t,p,r)
}

func TestCorrectiveAssetMissingGrantRejected(t *testing.T){
 p:=fixture();r:=registry(p);delete(r.Grants,"corrective_activation");reject(t,p,r)
}
func TestCorrectiveActivationReplacedRejected(t *testing.T){
 p:=fixture();r:=registry(p);p.Arms[1].CorrectiveActivationSHA256=h("a");reject(t,p,r)
}
func TestCorrectiveShapesLODMismatchRejected(t *testing.T){
 p:=fixture();r:=registry(p);p.Arms[3].CorrectiveShapesSHA256=h("a");reject(t,p,r)
}
func TestCorrectiveSwitchDisagreesWithArmRejected(t *testing.T){
 p:=fixture();r:=registry(p);p.Arms[1].ApplyCorrectives=false;reject(t,p,r)
}
func TestBlenderCannotClaimNativeCorrectiveMode(t *testing.T){
 p:=fixture();r:=registry(p);p.Arms[3].ApplyCorrectives=true;reject(t,p,r)
}
func TestNativeFBXDiffersFromPinnedSourceRejected(t *testing.T){
 p:=fixture();r:=registry(p);p.Clips[0].NativeFBXSHA256=h("a");reject(t,p,r)
}
func TestWrongNativeLODRejected(t *testing.T){
 p:=fixture();r:=registry(p);p.Clips[1].LOD=6;reject(t,p,r)
}
func TestWholeSourceSamplesRequired(t *testing.T){
 p:=fixture();r:=registry(p);p.Clips[1].SourceSampleCount=316;reject(t,p,r)
}
func TestClockRate120to24MustNotDrift(t *testing.T){
 p:=fixture();r:=registry(p);p.Arms[1].TargetHz=30;reject(t,p,r)
}
func TestNoInterpolatedOrDroppedSampleClaims(t *testing.T){
 p:=fixture();r:=registry(p);p.Clips[0].SamplingMethod="INTERPOLATED_24HZ";reject(t,p,r)
}
func TestExactLastIndexMustBePinned(t *testing.T){
 p:=fixture();r:=registry(p);p.Clips[1].LastSourceIndex=328;reject(t,p,r)
}
func TestClockPolicySHAChangeRejected(t *testing.T){
 p:=fixture();r:=registry(p);p.Arms[5].SamplingPolicySHA256=h("b");reject(t,p,r)
}
func TestPrivateVenueStillRequiresCorrectiveAssetSpecificGrant(t *testing.T){
 p:=fixture();p.Venue="private_github_actions";r:=registry(p)
 for id,g:=range r.Grants {g.Venue=p.Venue;g.Scope="PRIVATE_CLOUD_ADMITTED";r.Grants[id]=g}
 delete(r.Grants,"corrective_shapes_lod1");reject(t,p,r)
}

func TestIndependentSampleWitnessMissing(t *testing.T){
 p:=fixture();r:=registry(p);delete(r.Samples,"CMU07_01");reject(t,p,r)
}
func TestSampleWitnessReviewerAbsent(t *testing.T){
 p:=fixture();r:=registry(p);x:=r.Samples["CMU07_02"];x.Verified=false;r.Samples[x.ClipID]=x;reject(t,p,r)
}
func TestSampleWitnessWrongSourceSHA(t *testing.T){
 p:=fixture();r:=registry(p);x:=r.Samples["CMU07_01"];x.MotionSHA256=h("f");r.Samples[x.ClipID]=x;reject(t,p,r)
}
func TestSampleWitnessWrongPolicySHA(t *testing.T){
 p:=fixture();r:=registry(p);x:=r.Samples["CMU07_02"];x.PolicySHA256=h("f");r.Samples[x.ClipID]=x;reject(t,p,r)
}
func TestSampleWitnessMissingMiddleSourceTick(t *testing.T){
 p:=fixture();r:=registry(p);x:=r.Samples["CMU07_01"];x.Indices[22]+=1;r.Samples[x.ClipID]=x;reject(t,p,r)
}
func TestSampleWitnessDuplicatedSourceTick(t *testing.T){
 p:=fixture();r:=registry(p);x:=r.Samples["CMU07_02"];x.Indices[10]=x.Indices[9];r.Samples[x.ClipID]=x;reject(t,p,r)
}
func TestSampleWitnessIndexCountShort(t *testing.T){
 p:=fixture();r:=registry(p);x:=r.Samples["CMU07_02"];x.Indices=x.Indices[:65];r.Samples[x.ClipID]=x;reject(t,p,r)
}
func TestSampleManifestDigestMutationRejected(t *testing.T){
 p:=fixture();r:=registry(p);p.Clips[0].SampleManifestSHA256=h("e");reject(t,p,r)
}
func TestArmCannotReuseOtherClipSampleManifest(t *testing.T){
 p:=fixture();r:=registry(p);p.Arms[0].SampleManifestSHA256=p.Clips[1].SampleManifestSHA256;reject(t,p,r)
}
func TestWitnessCannotSelfGrantReviewerProof(t *testing.T){
 p:=fixture();r:=registry(p);x:=r.Samples["CMU07_02"];x.ReviewerProofSHA256="";r.Samples[x.ClipID]=x;reject(t,p,r)
}
func TestWitnessHashContentDisagrees(t *testing.T){
 p:=fixture();r:=registry(p);x:=r.Samples["CMU07_02"];x.ManifestSHA256=h("e");r.Samples[x.ClipID]=x;reject(t,p,r)
}
func TestSampleDigestDeterministicAndClipSpecific(t *testing.T){
 p:=fixture();r:=registry(p);a:=r.Samples["CMU07_01"];b:=r.Samples["CMU07_02"]
 x:=SampleManifestDigest(a.ClipID,a.MotionSHA256,a.PolicySHA256,a.SourceFrameCount,a.SourceHz,a.TargetHz,a.Indices)
 y:=SampleManifestDigest(a.ClipID,a.MotionSHA256,a.PolicySHA256,a.SourceFrameCount,a.SourceHz,a.TargetHz,a.Indices)
 if x!=y||x==b.ManifestSHA256||x!=p.Clips[0].SampleManifestSHA256{t.Fatalf("index transcript digest not reproducible/isolated")}
}
