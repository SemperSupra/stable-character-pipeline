package motion

import "testing"

// All inputs here are independent self-authored SYNTHETIC oracle coordinates.
// Green tests mean the new research gate prevents known false accepts; they
// do not authenticate a real detection or source witness.
func TestW7IndependentSyntheticCleanReference(t *testing.T) {
 var l,r [2]Detection
 l[0],r[0]=observe(-1.5,4)
 l[1],r[1]=observe(1.5,4)
 truth:=[2]Prior{{-1.5,4},{1.5,4}}
 ref:=SyntheticReference{Camera:Stereo{800,.4},Actors:truth,
   NoiseSigmaUpperBoundPixels:.5,MaxActorErrorMeters:.15,
   Calibrated:true,ActorPositionsMeasured:true,NoiseDistributionMeasured:true}
 got:=(Stereo{800,.4}).IndependentSyntheticAdmission(l,r,truth,ref)
 if got.Status!=Accept || got.Pairs[0].RightIndex!=0 || got.Pairs[1].RightIndex!=1 {
  t.Fatalf("clean original synthetic reference not admitted: %+v",got)
 }
}
func TestW7FalseActorPriorIndependentGroundTruthRejects(t *testing.T) {
 var l,r [2]Detection
 l[0],r[0]=observe(-.05,4)
 l[1],r[1]=observe(.05,4)
 wrong:=[2]Prior{{0,16.0/3},{0,16.0/5}}
 raw:=(Stereo{800,.4}).AssociateWithNoiseWitness(l,r,wrong,2,.15,.1,3)
 if raw.Status!=Accept || raw.Pairs[0].RightIndex!=1 {
  t.Fatalf("original frozen RED changed, re-evaluate: %+v",raw)
 }
 ref:=SyntheticReference{Camera:Stereo{800,.4},Actors:[2]Prior{{-.05,4},{.05,4}},
  NoiseSigmaUpperBoundPixels:.1,MaxActorErrorMeters:.15,
  Calibrated:true,ActorPositionsMeasured:true,NoiseDistributionMeasured:true}
 if got:=(Stereo{800,.4}).IndependentSyntheticAdmission(l,r,wrong,ref);got.Status==Accept {
  t.Fatalf("W7B_FALSE_PRIOR_WRONG_IDENTITY_WAS_ACCEPTED: %+v",got)
 }
 t.Log("W7B_BLUE_REFERENCE_REJECTS_PREVIOUS_WRONG_IDENTITY_RESEARCH_ONLY")
}
func TestW7WrongFocalIndependentCameraRejects(t *testing.T) {
 var l,r [2]Detection
 l[0],r[0]=observe(0,4)
 l[1],r[1]=observe(0,8)
 biased:=[2]Prior{{0,4.25},{0,8.5}}
 old:=(Stereo{850,.4}).AssociateWithNoiseWitness(l,r,biased,.8,.15,.1,3)
 if old.Status!=Accept {t.Fatalf("original focal negative changed: %+v",old)}
 ref:=SyntheticReference{Camera:Stereo{800,.4},Actors:[2]Prior{{0,4},{0,8}},
  NoiseSigmaUpperBoundPixels:.1,MaxActorErrorMeters:.15,
  Calibrated:true,ActorPositionsMeasured:true,NoiseDistributionMeasured:true}
 if got:=(Stereo{850,.4}).IndependentSyntheticAdmission(l,r,biased,ref);got.Status!=Reject {
  t.Fatalf("incorrect focal calibration falsely admitted: %+v",got)
 }
 t.Log("W7B_BLUE_WRONG_FOCAL_REJECTED_WITH_INDEPENDENT_CAMERA_REFERENCE")
}
func TestW7MissingExternalProvenanceAbstains(t *testing.T) {
 var l,r [2]Detection
 l[0],r[0]=observe(-1.5,4)
 l[1],r[1]=observe(1.5,4)
 truth:=[2]Prior{{-1.5,4},{1.5,4}}
 full:=SyntheticReference{Camera:Stereo{800,.4},Actors:truth,
 NoiseSigmaUpperBoundPixels:.5,MaxActorErrorMeters:.15,
 Calibrated:true,ActorPositionsMeasured:true,NoiseDistributionMeasured:true}
 for i:=0;i<3;i++ {
  q:=full
  switch i {case 0:q.Calibrated=false;case 1:q.ActorPositionsMeasured=false;case 2:q.NoiseDistributionMeasured=false}
  if got:=(Stereo{800,.4}).IndependentSyntheticAdmission(l,r,truth,q);got.Status!=Abstain {
   t.Fatalf("missing independent provenance %d accepted: %+v",i,got)
  }
 }
}
func TestW7UnderstatedNoiseUsesUpperBound(t *testing.T) {
 var l,r [2]Detection
 l[0],r[0]=observe(-.05,4)
 l[1],r[1]=observe(.05,4)
 truth:=[2]Prior{{-.05,4},{.05,4}}
 ref:=SyntheticReference{Camera:Stereo{800,.4},Actors:truth,
 NoiseSigmaUpperBoundPixels:6,MaxActorErrorMeters:.2,
 Calibrated:true,ActorPositionsMeasured:true,NoiseDistributionMeasured:true}
 if got:=(Stereo{800,.4}).IndependentSyntheticAdmission(l,r,truth,ref);got.Status==Accept {
  t.Fatalf("low separation under independent 6px upper noise was accepted: %+v",got)
 }
 ref.NoiseSigmaUpperBoundPixels=0
 if got:=(Stereo{800,.4}).IndependentSyntheticAdmission(l,r,truth,ref);got.Status!=Reject {
  t.Fatalf("zero uncalibrated sigma was accepted: %+v",got)
 }
}
