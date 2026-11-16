package main

import (
 "strings"
 "testing"
)
func TestClosedAndOpenSurfaceTopology(t *testing.T){
 closed:="v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 3 2\nf 1 2 4\nf 2 3 4\nf 3 1 4\n"
 m,e:=scanTopology(strings.NewReader(closed),4096,"FJsynthetic")
 if e!=nil||m.BoundaryEdges!=0||m.NonmanifoldEdges!=0||m.OrientedEdgeConflicts!=0||
  !m.ClosedEdgePairing||m.ConnectedVertexComponents!=1||m.Vertices!=4||m.Faces!=4{
  t.Fatalf("synthetic tetrahedron oracle %+v %v",m,e)
 }
 opened:="v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 3 2\nf 1 2 4\nf 2 3 4\n"
 m,e=scanTopology(strings.NewReader(opened),4096,"FJsynthetic")
 if e!=nil||m.ClosedEdgePairing||m.BoundaryEdges!=3{t.Fatalf("missing face falsely closed %+v %v",m,e)}
}
func TestDuplicateDirectionAndNonmanifold(t *testing.T){
 broken:="v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 2 3\nf 1 2 4\nf 1 2 3\n"
 m,e:=scanTopology(strings.NewReader(broken),4096,"FJsynthetic")
 if e!=nil||m.ClosedEdgePairing||m.NonmanifoldEdges==0{t.Fatalf("duplicate orientation/nonmanifold accepted %+v %v",m,e)}
}
func TestAtomicComponentOverlapNotNameEquality(t *testing.T){
 left:=[]Element{{ID:"FJ1",ConceptID:"FMA1"},{ID:"FJ2",ConceptID:"FMA1"}}
 right:=[]Element{{ID:"FJ2",ConceptID:"FMA2"},{ID:"FJ3",ConceptID:"FMA2"}}
 common:=intersect(left,right)
 if len(common)!=1||common[0]!="FJ2"{t.Fatal("actual atomic source set overlap lost")}
}
func TestInvalidUnboundedInput(t *testing.T){
 obj:="v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 2 3\nf 1 2 4\n"
 if _,e:=scanTopology(strings.NewReader(obj),5,"FJ");e==nil{t.Fatal("source cap not enforced")}
 obj="v 0 0 nan\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 2 3\nf 1 2 4\n"
 if _,e:=scanTopology(strings.NewReader(obj),4096,"FJ");e==nil{t.Fatal("nonfinite donor geometry admitted")}
}
