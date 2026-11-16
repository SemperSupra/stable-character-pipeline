package main
import(
 "strings"
 "testing"
)
func TestDiaphragmFJLikeTwoDisconnectedShells(t *testing.T){
 two:="v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 3 2\nf 1 2 4\nf 2 3 4\nf 3 1 4\n"
 two+="v 5 0 0\nv 6 0 0\nv 5 1 0\nv 5 0 1\nf 5 7 6\nf 5 6 8\nf 6 7 8\nf 7 5 8\n"
 m,e:=originalMesh(strings.NewReader(two),4096);if e!=nil{t.Fatal(e)}
 r,e:=forensic(m)
 if e!=nil||r.VertexConnectedComponentCount!=2||r.EdgeConnectedFaceComponents!=2||
   r.BoundaryEdges!=0||r.NonmanifoldEdges!=0||r.Status!="HOLD_DIAPHRAGM_NONMANIFOLD_OR_DISCONNECTED"{
   t.Fatalf("disconnected shells incorrectly admitted %+v %v",r,e)
 }
}
func TestSourceDuplicateFacesAndNonmanifoldEdgeIncidence(t *testing.T){
 tetra:="v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 3 2\nf 1 2 4\nf 2 3 4\nf 3 1 4\nf 1 3 2\n"
 m,e:=originalMesh(strings.NewReader(tetra),4096);if e!=nil{t.Fatal(e)}
 r,e:=forensic(m)
 if e!=nil||r.SourceDuplicateFaces!=2||r.NonmanifoldEdges==0||len(r.NonmanifoldExamples)==0||
  r.Status!="HOLD_DIAPHRAGM_NONMANIFOLD_OR_DISCONNECTED"{t.Fatalf("duplicated face graph missed %+v %v",r,e)}
}
func TestExactSourceSeamDuplicatedIndicesNotExtraComponents(t *testing.T){
 split:="v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nv 0 0 0\nf 5 3 2\nf 1 2 4\nf 2 3 4\nf 3 1 4\n"
 m,e:=originalMesh(strings.NewReader(split),4096);if e!=nil{t.Fatal(e)}
 r,e:=forensic(m)
 if e!=nil||r.ExactMerged!=1||r.VertexConnectedComponentCount!=1||r.EdgeConnectedFaceComponents!=1||
  r.BoundaryEdges!=0||r.NonmanifoldEdges!=0||r.Status!="SOURCE_TOPOLOGY_CANDIDATE_NEEDS_SELF_INTERSECTION_AND_VOLUME"{
  t.Fatalf("exact indexed source split misclassified %+v %v",r,e)
 }
}
