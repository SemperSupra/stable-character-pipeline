package jointmap

import (
 "encoding/json"
 "fmt"
 "math"
 "strings"
 "testing"
)
func h(s string)string{return strings.Repeat(s,64)}
func fixture()Plan{
 p:=Plan{Schema:Schema,Native:Rig{SHA256:h("a"),PoseSpace:"MHR_LOCAL_JOINT"},
  Blender:Rig{SHA256:h("b"),PoseSpace:"BLENDER_IMPORTED_BONE_LOCAL"},
  Omission:Omission{Native:"n000",Explanation:"synthetic nondeforming omitted top root"},
  Alignment:Alignment{Rotation:[9]float64{1,0,0,0,1,0,0,0,1},Scale:2,Translation:V3{2,3,4},MaxError:.0001},
  SourceRights:"REVIEW_REQUIRED_NO_PERMISSION_INFERRED",
 }
 for i:=0;i<127;i++{
  id:=fmt.Sprintf("n%03d",i)
  side:="center"
  if i>1&&i%3==0{side="left"}else if i>1&&i%3==1{side="right"}
  parent:=""
  if i>0{parent=fmt.Sprintf("n%03d",i-1)}
  loc:=V3{float64(i)*.13,math.Sin(float64(i)*.25),math.Cos(float64(i)*.1)}
  p.Native.Joints=append(p.Native.Joints,Joint{ID:id,Parent:parent,Side:side,Deforming:i>0,RestWorld:loc})
  if i>0{
   targetParent:="";if i>1{targetParent=fmt.Sprintf("b%03d",i-1)}
   p.Blender.Joints=append(p.Blender.Joints,Joint{ID:fmt.Sprintf("b%03d",i),Parent:targetParent,Side:side,Deforming:true,
    RestWorld:transform(loc,p.Alignment)})
   p.Pairs=append(p.Pairs,Pair{Native:id,Blender:fmt.Sprintf("b%03d",i)})
  }
 }
 return p
}
func trusted(p Plan)Trust{
 witness:=LBSWitness{NativeSHA256:p.Native.SHA256,LOD:1,VertexCount:18439}
 for _,j:=range p.Native.Joints {
  inf:=Influence{JointID:j.ID}
  if j.Deforming {inf.NonzeroVertices=3;inf.MaxAbsoluteWeight=.7;inf.SumAbsoluteWeight=1.2}
  witness.Joints=append(witness.Joints,inf)
 }
 return Trust{NativeSHA256:p.Native.SHA256,
 BlenderSHA256:p.Blender.SHA256,PairMapSHA256:PairMapDigest(p),
 AlignmentSHA256:AlignmentDigest(p.Alignment),AlignmentReviewSHA256:h("d"),
 MaxTrustedRestError:p.Alignment.MaxError,
 OmittedID:p.Omission.Native,OmissionReviewSHA256:h("f"),MapReviewed:true,
 LBS:witness,LBSWitnessSHA256:InfluenceDigest(witness),LBSReviewSHA256:h("e"),
 }
}
func checkReject(t *testing.T,p Plan,tr Trust){
 t.Helper();v,e:=Validate(p,tr)
 if e==nil{t.Fatalf("invalid mapping accepted: %+v",v)}
 if v.Status=="PASS_SYNTHETIC_STRUCTURAL_ONLY__REAL_RIG_PARITY_UNKNOWN"||v.CanonicalCharacterPack!="HOLD_OWNER_HUMAN_ONLY"{
  t.Fatalf("rejection promoted product claim: %+v",v)
 }
}
func TestSynthetic127To126StructuralPassStillNoNativeTruth(t *testing.T){
 p:=fixture();v,e:=Validate(p,trusted(p))
 if e!=nil{t.Fatal(e)}
 if v.Matched!=126||v.Native!=127||v.Blender!=126||v.MaxRestError>1e-8||
  v.Status!="PASS_SYNTHETIC_STRUCTURAL_ONLY__REAL_RIG_PARITY_UNKNOWN"||
  v.ActualNativeRuntime!="NOT_RUN"{t.Fatal(v)}
}
func TestNoIndependentReview(t *testing.T){
 p:=fixture();tr:=trusted(p);tr.MapReviewed=false;checkReject(t,p,tr)
}
func TestSourceScenePinConflict(t *testing.T){
 p:=fixture();tr:=trusted(p);p.Native.SHA256=h("c");checkReject(t,p,tr)
}
func TestForgedPairWithoutAttestation(t *testing.T){
 p:=fixture();tr:=trusted(p);p.Pairs[0].Blender="b002";checkReject(t,p,tr)
}
func TestUnreviewedOmission(t *testing.T){
 p:=fixture();tr:=trusted(p);tr.OmissionReviewSHA256="fake";checkReject(t,p,tr)
}
func TestOmittedDeformingJoint(t *testing.T){
 p:=fixture();p.Native.Joints[0].Deforming=true;checkReject(t,p,trusted(p))
}
func TestNonUniqueNativeJoint(t *testing.T){
 p:=fixture();p.Native.Joints[1].ID="n000";checkReject(t,p,trusted(p))
}
func TestCyclicSourceHierarchy(t *testing.T){
 p:=fixture();p.Native.Joints[2].Parent="n003";checkReject(t,p,trusted(p))
}
func TestWrongTargetAncestry(t *testing.T){
 p:=fixture();p.Blender.Joints[3].Parent="b001";checkReject(t,p,trusted(p))
}
func TestBilateralMirrorMapRejected(t *testing.T){
 p:=fixture();p.Pairs[0].Blender="b003";p.Pairs[2].Blender="b001"
 checkReject(t,p,trusted(p))
}
func TestBadReferenceAlignmentScale(t *testing.T){
 p:=fixture();p.Alignment.Scale=0;checkReject(t,p,trusted(p))
}
func TestReflectedAlignmentRejected(t *testing.T){
 p:=fixture();p.Alignment.Rotation[0]=-1;checkReject(t,p,trusted(p))
}
func TestShearedAlignmentRejected(t *testing.T){
 p:=fixture();p.Alignment.Rotation[1]=0.1;checkReject(t,p,trusted(p))
}
func TestMismatchedRestPosition(t *testing.T){
 p:=fixture();p.Blender.Joints[55].RestWorld[0]+=0.11;checkReject(t,p,trusted(p))
}
func TestBadFrameTolerance(t *testing.T){
 p:=fixture();p.Alignment.MaxError=1;checkReject(t,p,trusted(p))
}
func TestNonfiniteRestCoordinate(t *testing.T){
 p:=fixture();p.Native.Joints[22].RestWorld[1]=math.NaN();checkReject(t,p,trusted(p))
}
func TestNoPoseSpaceInference(t *testing.T){
 p:=fixture();p.Blender.PoseSpace="UNKNOWN";checkReject(t,p,trusted(p))
}
func TestPlanCannotGrantSourceRights(t *testing.T){
 p:=fixture();p.SourceRights="PERMIT_MODEL_WEIGHTS";checkReject(t,p,trusted(p))
}
func TestMissingActualNativeJoint(t *testing.T){
 p:=fixture();p.Native.Joints=p.Native.Joints[:126];checkReject(t,p,trusted(p))
}
func TestJointCountNotJustInteger(t *testing.T){
 p:=fixture();p.Blender.Joints=append(p.Blender.Joints,p.Blender.Joints[0]);checkReject(t,p,trusted(p))
}
func TestStrictDecoderRejectsUnknownAndConcatenation(t *testing.T){
 p:=fixture();b,e:=json.Marshal(p);if e!=nil{t.Fatal(e)}
 q,e:=DecodeStrict(b);if e!=nil||len(q.Pairs)!=126{t.Fatalf("roundtrip failed: %v",e)}
 if _,e:=DecodeStrict(append(b,b...));e==nil{t.Fatal("concatenated JSON passed")}
 s:=strings.Replace(string(b),"\"schema\":","\"injected\":true,\"schema\":",1)
 if _,e:=DecodeStrict([]byte(s));e==nil{t.Fatal("unknown field passed")}
}

func TestMissingIndependentAlignmentReview(t *testing.T){
 p:=fixture();tr:=trusted(p);tr.AlignmentReviewSHA256="";checkReject(t,p,tr)
}
func TestCandidateAlignmentChangedAfterReview(t *testing.T){
 p:=fixture();tr:=trusted(p);p.Alignment.Translation[0]+=1;checkReject(t,p,tr)
}
func TestCandidateCannotExpandRestResidual(t *testing.T){
 p:=fixture();tr:=trusted(p);p.Alignment.MaxError*=5;checkReject(t,p,tr)
}
func TestRotation90DegreesAndTranslation(t *testing.T){
 p:=fixture();p.Alignment.Rotation=[9]float64{0,-1,0,1,0,0,0,0,1}
 p.Alignment.Translation=V3{7,-4,2}
 for i:=range p.Pairs {
  p.Blender.Joints[i].RestWorld=transform(p.Native.Joints[i+1].RestWorld,p.Alignment)
 }
 v,e:=Validate(p,trusted(p))
 if e!=nil||v.Matched!=126{t.Fatalf("proper rotated space was rejected: %v %+v",e,v)}
}

func TestNoIndependentLBSReview(t *testing.T){
 p:=fixture();tr:=trusted(p);tr.LBSReviewSHA256="";checkReject(t,p,tr)
}
func TestNoNativeLOD1InfluenceCensus(t *testing.T){
 p:=fixture();tr:=trusted(p);tr.LBS.Joints=nil;checkReject(t,p,tr)
}
func TestInfluenceMissingLastJoint(t *testing.T){
 p:=fixture();tr:=trusted(p);tr.LBS.Joints=tr.LBS.Joints[:126]
 tr.LBSWitnessSHA256=InfluenceDigest(tr.LBS);checkReject(t,p,tr)
}
func TestInfluenceDuplicatedJoint(t *testing.T){
 p:=fixture();tr:=trusted(p);tr.LBS.Joints[2].JointID=tr.LBS.Joints[3].JointID
 tr.LBSWitnessSHA256=InfluenceDigest(tr.LBS);checkReject(t,p,tr)
}
func TestOmittedJointActuallyHasNonzeroWeights(t *testing.T){
 p:=fixture();tr:=trusted(p)
 tr.LBS.Joints[0].NonzeroVertices=1
 tr.LBS.Joints[0].MaxAbsoluteWeight=.001
 tr.LBS.Joints[0].SumAbsoluteWeight=.001
 tr.LBSWitnessSHA256=InfluenceDigest(tr.LBS)
 checkReject(t,p,tr)
}
func TestZeroInfluenceWithPositiveWeightRejected(t *testing.T){
 p:=fixture();tr:=trusted(p);tr.LBS.Joints[0].MaxAbsoluteWeight=.01
 tr.LBSWitnessSHA256=InfluenceDigest(tr.LBS);checkReject(t,p,tr)
}
func TestDeformingFalseButLBSPositive(t *testing.T){
 p:=fixture();p.Native.Joints[1].Deforming=false
 tr:=trusted(p)
 tr.LBS.Joints[1].NonzeroVertices=2
 tr.LBS.Joints[1].MaxAbsoluteWeight=.8
 tr.LBS.Joints[1].SumAbsoluteWeight=1.1
 tr.LBSWitnessSHA256=InfluenceDigest(tr.LBS)
 checkReject(t,p,tr)
}
func TestWrongLODInfluenceRejected(t *testing.T){
 p:=fixture();tr:=trusted(p);tr.LBS.LOD=2
 tr.LBSWitnessSHA256=InfluenceDigest(tr.LBS);checkReject(t,p,tr)
}
func TestWrongNativeSourceInfluenceRejected(t *testing.T){
 p:=fixture();tr:=trusted(p);tr.LBS.NativeSHA256=h("c")
 tr.LBSWitnessSHA256=InfluenceDigest(tr.LBS);checkReject(t,p,tr)
}
func TestUntrustedAlteredCensusDigestRejected(t *testing.T){
 p:=fixture();tr:=trusted(p);tr.LBS.Joints[10].MaxAbsoluteWeight=.33
 checkReject(t,p,tr)
}
func TestOverunitWeightRejected(t *testing.T){
 p:=fixture();tr:=trusted(p);tr.LBS.Joints[12].MaxAbsoluteWeight=1.1
 tr.LBSWitnessSHA256=InfluenceDigest(tr.LBS);checkReject(t,p,tr)
}
func TestNegativeVertexCountRejected(t *testing.T){
 p:=fixture();tr:=trusted(p);tr.LBS.VertexCount=-1
 tr.LBSWitnessSHA256=InfluenceDigest(tr.LBS);checkReject(t,p,tr)
}
func TestNonnumericWeightRejected(t *testing.T){
 p:=fixture();tr:=trusted(p);tr.LBS.Joints[8].SumAbsoluteWeight=math.NaN()
 checkReject(t,p,tr)
}
