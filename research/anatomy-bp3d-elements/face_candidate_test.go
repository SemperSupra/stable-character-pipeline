package main

import(
 "strings"
 "testing"
)
func syntheticTetra()string{
 return "v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 3 2\nf 1 2 4\nf 2 3 4\nf 3 1 4\n"
}
func TestSourceSameWindingCyclicDuplicateRemovedOnlyInDerivedCandidate(t *testing.T){
 obj:=syntheticTetra()+"f 3 2 1\n"
 m,e:=originalMesh(strings.NewReader(obj),4096);if e!=nil{t.Fatal(e)}
 before:=len(m.Faces)
 out,e:=diagnoseFaceCopies(m)
 if e!=nil||out.ExactSameWindingDuplicates!=1||out.ReverseWindingCoincident!=0||
    out.BeforeNonmanifoldEdges==0||out.AfterNonmanifoldEdges!=0||out.AfterBoundaryEdges!=0||
    out.AfterComponents!=1||out.Status!="DERIVED_COMPONENT_TOPOLOGY_CANDIDATE_PHYSICS_HOLD"{
  t.Fatalf("same winding candidate unexpected %+v %v",out,e)
 }
 if len(m.Faces)!=before||out.CandidateFaces!=before-1||!out.OriginalMeshImmutable{
  t.Fatal("original source faces were edited")
 }
}
func TestReversedTriangleCoincidenceNeverAutomaticallyDeleted(t *testing.T){
 obj:=syntheticTetra()+"f 1 2 3\n"
 m,e:=originalMesh(strings.NewReader(obj),4096);if e!=nil{t.Fatal(e)}
 out,e:=diagnoseFaceCopies(m)
 if e!=nil||out.ReverseWindingCoincident==0||out.ExactSameWindingDuplicates!=0||
 out.CandidateFaces!=len(m.Faces)||out.Status!="HOLD_NO_EXACT_SAME_WINDING_FACE_DUPLICATES"{
  t.Fatalf("reversed source face must stay held %+v %v",out,e)
 }
}
func TestNoSilentRemovalOfDisconnectedFragments(t *testing.T){
 obj:=syntheticTetra()
 obj+="v 10 0 0\nv 11 0 0\nv 10 1 0\nv 10 0 1\nf 5 7 6\nf 5 6 8\nf 6 7 8\nf 7 5 8\n"
 obj+="f 3 2 1\n"
 m,e:=originalMesh(strings.NewReader(obj),4096);if e!=nil{t.Fatal(e)}
 out,e:=diagnoseFaceCopies(m)
 if e!=nil||out.AfterComponents!=2||out.OtherComponents!=1||
    out.Status!="HOLD_DERIVED_DIAPHRAGM_STILL_MULTICOMPONENT_OR_NONMANIFOLD"{
  t.Fatalf("forensic removed disconnected source organ fragment %+v %v",out,e)
 }
}
func TestDeterministicCyclicIdentity(t *testing.T){
 a:=[]int{4,1,2,3}
 b:=[]int{2,3,4,1}
 c:=[]int{4,3,2,1}
 if exactCyclic(a)!=exactCyclic(b)||exactCyclic(a)==exactCyclic(c){
  t.Fatal("cyclic duplicate classifier ignored winding")
 }
}
