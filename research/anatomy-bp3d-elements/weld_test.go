package main
import (
 "strings"
 "testing"
)
func TestDuplicateSeamVertexCanCloseOnlyAsCandidate(t *testing.T){
 // Exact duplicate of canonical vertex #1, used on only one tetra face.
 source:="v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nv 0 0 0\nf 5 3 2\nf 1 2 4\nf 2 3 4\nf 3 1 4\n"
 m,e:=originalMesh(strings.NewReader(source),4096)
 if e!=nil{t.Fatal(e)}
 r,e:=checkMeshAfterWeld(m,.001)
 if e!=nil||r.VerticesMerged!=1||r.CandidateVertices!=4||r.BoundaryEdges!=0||
  r.NonmanifoldEdges!=0||r.Components!=1||
  r.Status!="EDGE_PAIRED_AFTER_PROPOSED_WELD_NOT_ANATOMICAL_ACCEPTANCE"{
  t.Fatalf("seam closure candidate incorrectly evaluated: %+v %v",r,e)
 }
}
func TestTrueHoleRemainsHoleAfterWeld(t *testing.T){
 source:="v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 3 2\nf 1 2 4\nf 2 3 4\n"
 m,e:=originalMesh(strings.NewReader(source),4096);if e!=nil{t.Fatal(e)}
 a,e:=checkMeshAfterWeld(m,.01)
 if e!=nil||a.BoundaryEdges!=3||a.Status!="HOLD_OPEN_OR_NONMANIFOLD_AFTER_PROPOSED_WELD"{
  t.Fatalf("welding fabricated missing anatomical triangle: %+v %v",a,e)
 }
}
func TestWeldCollapseAndUnsafeToleranceReported(t *testing.T){
 source:="v 0 0 0\nv 0.0001 0 0\nv 0 1 0\nv 0 0 1\nf 1 3 4\nf 2 3 4\n"
 m,e:=originalMesh(strings.NewReader(source),4096);if e!=nil{t.Fatal(e)}
 a,e:=checkMeshAfterWeld(m,.001)
 if e!=nil||a.VerticesMerged==0||a.OrientedConflicts==0||a.Status!="HOLD_OPEN_OR_NONMANIFOLD_AFTER_PROPOSED_WELD"{
  t.Fatalf("collapsed source not properly held: %+v %v",a,e)
 }
 for _,tol:=range []float64{0,-.1,.1}{
  if _,e:=checkMeshAfterWeld(m,tol);e==nil{t.Fatal("unsafe tolerance admitted",tol)}
 }
}
func TestFailOnNonFiniteDonorGeometry(t *testing.T){
 source:="v 0 0 0\nv inf 0 0\nv 0 1 0\nv 0 0 1\nf 1 2 3\nf 1 3 4\n"
 if _,e:=originalMesh(strings.NewReader(source),4096);e==nil{t.Fatal("nonfinite mesh source admitted")}
}
