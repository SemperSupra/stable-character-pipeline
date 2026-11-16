package fidelity

import (
 "strings"
 "testing"
)
const h="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
func fixture() Feature {
 return Feature{Schema:Schema,ID:"lung-left",
 CanonicalOntology:"FMA",CanonicalConceptID:"FMA7310",
 Representations:[]Representation{
  {Source:"BodyParts3D",Version:"4.0",View:"ISA",Ontology:"FMA",ConceptID:"FMA7310",
   GeometryID:"BP100",AssetSHA256:h,Rights:"ADMITTED",Frame:"BP3D_ZUP_MM",
   GeometryVertices:8000,SourceImportObserved:true},
  {Source:"BodyParts3D",Version:"4.0",View:"PART_OF",Ontology:"FMA",ConceptID:"FMA7310",
   GeometryID:"BP900",AssetSHA256:h,Rights:"ADMITTED",Frame:"BP3D_ZUP_MM",
   GeometryVertices:10000,SourceImportObserved:true},
 }}
}
func TestDistinctOntologyViewsShareConceptButNotGeometry(t *testing.T){
 f:=fixture()
 if err:=Validate(f);err!=nil{t.Fatal(err)}
 a,err:=Evaluate(f,L0);if err!=nil{t.Fatal(err)}
 if len(a.GeometrySources)!=2||a.Status!="EVIDENCE_CONTRACT_COMPLETE_REVIEW_REQUIRED"{t.Fatal(a)}
 f.Representations[1].GeometryID=f.Representations[0].GeometryID
 // Same geometry name in different source tree is permitted because source
 // identity is namespaced; it does not certify that the binary bytes match.
 if e:=Validate(f);e!=nil{t.Fatal(e)}
 f.Representations[1].View=f.Representations[0].View
 if e:=Validate(f);e==nil{t.Fatal("same source+view+geometry collision accepted")}
}
func TestThreeFidelityTiersFailClosed(t *testing.T){
 f:=fixture()
 for _,target:=range []Tier{L1,L2}{
  verdict,err:=Evaluate(f,target);if err!=nil{t.Fatal(err)}
  if !strings.HasPrefix(verdict.Status,"HOLD")||len(verdict.Missing)==0{t.Fatal(verdict)}
 }
 f.Rig=RigEvidence{NativeRig:"MPFB_default",RigRevision:"pinned",
  AttachmentID:"spine01",PoseReceiptSHA256:h,RefitReceiptSHA256:h}
 f.Render=ProductionEvidence{VisualReviewReceiptSHA256:h,SavedSceneReceiptSHA256:h,InterchangeReceiptSHA256:h}
 verdict,err:=Evaluate(f,L1);if err!=nil||verdict.Status!="EVIDENCE_CONTRACT_COMPLETE_REVIEW_REQUIRED"{t.Fatal(verdict,err)}
 verdict,err=Evaluate(f,L2);if err!=nil||len(verdict.Missing)!=2{t.Fatal(verdict,err)}
 f.Solver=SolverEvidence{Solver:"synthetic",Version:"test",MaterialModel:"toy",
  CollisionReceiptSHA256:h,SignedJacobianReceiptSHA256:h,TemporalReceiptSHA256:h}
 verdict,err=Evaluate(f,L2);if err!=nil||verdict.Status!="EVIDENCE_CONTRACT_COMPLETE_REVIEW_REQUIRED"{t.Fatal(verdict,err)}
 // This proves only fields can be provided, not the truth of their receipts.
}
func TestNoFakeGeometryFromNamesOrUnknownRights(t *testing.T){
 f:=fixture()
 f.Representations[0].SourceImportObserved=false
 f.Representations[1].Rights="UNKNOWN"
 r,err:=Evaluate(f,L0)
 if err!=nil||len(r.Missing)!=1{t.Fatalf("%+v %v",r,err)}
 f.Representations[1].Rights="DENIED"
 r,err=Evaluate(f,L0)
 if err!=nil||len(r.Missing)!=1{t.Fatalf("%+v %v",r,err)}
 f.Representations[1].Rights="ADMITTED"
 f.Representations[1].AssetSHA256="not-a-hash"
 if e:=Validate(f);e==nil{t.Fatal("bad cryptographic source tag admitted")}
}
func TestNoAutomaticFMAUberonCrosswalk(t *testing.T){
 x:=Crosswalk{FromOntology:"FMA",FromID:"FMA7310",ToOntology:"UBERON",ToID:"UBERON:0002185",ReviewStatus:"PROPOSED",EvidenceSHA256:h}
 if CrosswalkEligible(x){t.Fatal("unreviewed crosswalk approved")}
 x.ReviewStatus="REVIEWED"
 if !CrosswalkEligible(x){t.Fatal("valid reviewed explicit mapping blocked")}
 x.EvidenceSHA256=""
 if CrosswalkEligible(x){t.Fatal("unproven crosswalk approved")}
}
func TestViewAndPhysicsAreOrthogonal(t *testing.T){
 f:=fixture()
 f.Rig=RigEvidence{NativeRig:"MPFB",RigRevision:"p",AttachmentID:"spine01"}
 before:=PhysicsStateDigest(f)
 f.Visible=!f.Visible
 if after:=PhysicsStateDigest(f);before!=after{t.Fatal("hidden anatomy changed physics digest")}
 f.CollisionActive=true
 if after:=PhysicsStateDigest(f);before==after{t.Fatal("collision flag excluded from physics digest")}
}
func TestBadConceptsAndTiersRejected(t *testing.T){
 f:=fixture()
 f.CanonicalConceptID="UBERON:0002185"
 if e:=Validate(f);e==nil{t.Fatal("ontology name/id mismatch")}
 f=fixture()
 if _,e:=Evaluate(f,Tier("L3"));e==nil{t.Fatal("unrecognized tier allowed")}
}
