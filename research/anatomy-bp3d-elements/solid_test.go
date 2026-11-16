package main

import (
 "math"
 "strings"
 "testing"
)
func TestExactSeamTetrahedronPositiveVolumeAndTranslation(t *testing.T){
 src:="v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nv 0 0 0\nf 5 3 2\nf 1 2 4\nf 2 3 4\nf 3 1 4\n"
 m,e:=originalMesh(strings.NewReader(src),4096);if e!=nil{t.Fatal(e)}
 x,e:=signedVolumeCandidate(m,"FJ_TEST")
 if e!=nil||x.Status!="CANDIDATE_SIGNED_VOLUME_SURFACE_ONLY"||x.OpenEdges!=0||x.Components!=1||
    x.DuplicateVertexIndices!=1||x.SignedVolumeRawUnitsCubed==nil||
    math.Abs(*x.SignedVolumeRawUnitsCubed-1.0/6)>1e-10{
  t.Fatalf("no valid candidate after exact duplicate remap %+v error %v",x,e)
 }
 // Signed volume must not depend on an arbitrary coordinate-origin shift.
 for i:=range m.Vertices{
  m.Vertices[i].X+=1200;m.Vertices[i].Y-=3400;m.Vertices[i].Z+=750
 }
 y,e:=signedVolumeCandidate(m,"FJ_TEST_TRANSLATED")
 if e!=nil||y.SignedVolumeRawUnitsCubed==nil||
    math.Abs(*y.SignedVolumeRawUnitsCubed-1.0/6)>1e-8{t.Fatalf("unstable translated candidate %+v %v",y,e)}
}
func TestInwardAndOpenSurfacesMustStayHold(t *testing.T){
 inward:="v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 2 3\nf 1 4 2\nf 2 4 3\nf 3 4 1\n"
 m,e:=originalMesh(strings.NewReader(inward),4096);if e!=nil{t.Fatal(e)}
 x,e:=signedVolumeCandidate(m,"SYNTHETIC_INWARD")
 if e!=nil||x.Status!="HOLD_INWARD_OR_ZERO_SIGNED_VOLUME"||x.SignedVolumeRawUnitsCubed==nil||
  *x.SignedVolumeRawUnitsCubed>=0{t.Fatalf("inward winding accepted %+v %v",x,e)}
 opened:="v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 3 2\nf 1 2 4\nf 2 3 4\n"
 m,e=originalMesh(strings.NewReader(opened),4096);if e!=nil{t.Fatal(e)}
 y,e:=signedVolumeCandidate(m,"SYNTHETIC_OPEN")
 if e!=nil||y.SignedVolumeRawUnitsCubed!=nil||y.OpenEdges==0||y.Status!="HOLD_NONMANIFOLD_OPEN_OR_MULTICOMPONENT_SOLID"{
  t.Fatalf("missing source face considered solid %+v %v",y,e)
 }
}
func TestDiaphragmLikeDisconnectedClosedShellsNotAutomaticallyOneOrgan(t *testing.T){
 src:="v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 3 2\nf 1 2 4\nf 2 3 4\nf 3 1 4\n"
 src+="v 10 0 0\nv 11 0 0\nv 10 1 0\nv 10 0 1\nf 5 7 6\nf 5 6 8\nf 6 7 8\nf 7 5 8\n"
 m,e:=originalMesh(strings.NewReader(src),4096);if e!=nil{t.Fatal(e)}
 x,e:=signedVolumeCandidate(m,"SYNTHETIC_MULTICOMPONENT")
 if e!=nil||x.Components!=2||x.SignedVolumeRawUnitsCubed!=nil||x.Status!="HOLD_NONMANIFOLD_OPEN_OR_MULTICOMPONENT_SOLID"{
  t.Fatalf("multiple disconnected shells silently accepted %+v %v",x,e)
 }
}
func TestRejectInvalidOriginalVertexIndex(t *testing.T){
 m:=meshData{Vertices:[]vertex{{0,0,0},{1,0,0},{0,1,0},{0,0,1}},
  Faces:[][]int{{0,1,2},{0,1,17}}}
 if _,e:=signedVolumeCandidate(m,"BAD_INDEX");e==nil{t.Fatal("invalid source index accepted")}
}
