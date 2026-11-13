package shellqa

import (
 "math"
 "testing"
)

func nearly(t *testing.T,a,b float64) {
 t.Helper()
 if math.Abs(a-b)>1e-10 {t.Fatalf("not close: %.14g / %.14g",a,b)}
}
func must(t *testing.T,rest,posed Mesh) Receipt {
 t.Helper()
 r,e:=Analyze(rest,posed);if e!=nil {t.Fatal(e)}
 if r.SelfIntersection!="UNKNOWN_BVH_NOT_EXECUTED"||r.PoseAnatomy!="UNKNOWN_NOT_TESTED" {t.Fatalf("false qualification: %+v",r)}
 return r
}
func TestRigidRotation_ProperRotationNotFold(t *testing.T) {
 rest:=Patch()
 for _,degrees:=range []float64{0,45,120,180,270} {
  r:=must(t,rest,RotateY(rest,degrees))
  if r.OpposingInteriorHinges!=0||r.SevereAreaCollapses!=0 {t.Fatalf("%v improper fold alert %+v",degrees,r)}
  nearly(t,r.MaxAbsoluteEdgeStrain,0)
  if r.ManifoldInteriorEdges!=1 {t.Fatal(r)}
  if degrees==120&&r.LegacyRestNormalReversals!=2 {t.Fatalf("old normal diagnostic should flag 2: %+v",r)}
 }
}
func TestTranslationIsInvariant(t *testing.T) {
 a:=Patch();b:=Clone(a)
 for i,v:=range b.Vertices {b.Vertices[i]=Vec3{v.X+3,v.Y-8,v.Z+2}}
 r:=must(t,a,b)
 if r.LegacyRestNormalReversals!=0||r.OpposingInteriorHinges!=0||r.SevereAreaCollapses!=0 {t.Fatal(r)}
 nearly(t,r.MaxAbsoluteEdgeStrain,0)
}
func TestHingeFoldFlag_WithoutAreaCollapse(t *testing.T) {
 a:=Patch();r:=must(t,a,Hinge(a,160))
 if r.OpposingInteriorHinges!=1 {t.Fatal(r)}
 if r.SevereAreaCollapses!=0 {t.Fatal(r)}
 nearly(t,r.MaxAbsoluteEdgeStrain,0)
}
func TestNaturalHingeBendDoesNotTriggerOpposition(t *testing.T) {
 a:=Patch();r:=must(t,a,Hinge(a,45))
 if r.OpposingInteriorHinges!=0||r.SevereAreaCollapses!=0 {t.Fatal(r)}
}
func TestDegenerateAreaIndependentOfNormalReversal(t *testing.T) {
 a:=Patch();b:=Clone(a);b.Vertices[3]=Vec3{.5,0,0}
 r:=must(t,a,b)
 if r.SevereAreaCollapses!=1 {t.Fatalf("missing area collapse %+v",r)}
}
func TestStrongStrainDetected(t *testing.T) {
 a:=Patch();b:=Clone(a)
 for i,v:=range b.Vertices {b.Vertices[i]=Vec3{3*v.X,v.Y,v.Z}}
 r:=must(t,a,b)
 if r.MaxAbsoluteEdgeStrain<1.0 {t.Fatalf("missing strain %+v",r)}
}
func TestFaceOrderOrWindingChangeRejected(t *testing.T) {
 a:=Patch();b:=Clone(a);b.Faces[0]=Triangle{1,0,2}
 if _,e:=Analyze(a,b);e==nil {t.Fatal("changed winding was accepted")}
}
func TestNonmanifoldSharedEdgeRejected(t *testing.T) {
 a:=Patch()
 a.Vertices=append(a.Vertices,Vec3{.5,0,1})
 a.Faces=append(a.Faces,Triangle{0,1,4})
 if _,e:=Analyze(a,a);e==nil {t.Fatal("non-manifold edge accepted")}
}
func TestNonfiniteVertexRejected(t *testing.T) {
 a:=Patch();b:=Clone(a);b.Vertices[2].Z=math.NaN()
 if _,e:=Analyze(a,b);e==nil {t.Fatal("nonfinite accepted")}
}
func TestMirrorGlobal_CannotClaimAnatomicalPass(t *testing.T) {
 a:=Patch();b:=Clone(a)
 for i,v:=range b.Vertices {b.Vertices[i]=Vec3{-v.X,v.Y,v.Z}}
 r:=must(t,a,b)
 if r.OpposingInteriorHinges!=0||r.SevereAreaCollapses!=0 {t.Fatal(r)}
 if r.LegacyRestNormalReversals!=2 {t.Fatal(r)}
 // Explicit negative control: an open shell cannot alone prove mirror/fold status.
 if r.Status!="PASS_DIAGNOSTICS_ONLY__REAL_MHR_AND_RELEASE_HOLD" {t.Fatal("false acceptance",r.Status)}
}
