package diaphragm

import "testing"

func TestReversePairIsNotAutomaticallyDeleted(t *testing.T) {
 faces:=[]Face{{0,1,2},{0,2,1}}
 r,e:=Inspect(faces);if e!=nil {t.Fatal(e)}
 if r.TotalFaces!=2 || len(r.OppositePairs)!=1 || r.OppositePairs[0]!=(OppositePair{0,1}) {t.Fatalf("unexpected preserved face report: %+v",r)}
 if len(r.FourFaceEdges)!=0 {t.Fatalf("unexpected edge incidence: %+v",r)}
}
func TestFourIncidentFaceEdgeIsDetected(t *testing.T) {
 faces:=[]Face{{0,1,2},{1,0,3},{0,1,4},{1,0,5}}
 r,e:=Inspect(faces);if e!=nil {t.Fatal(e)}
 if len(r.FourFaceEdges)!=1 || r.FourFaceEdges[0]!=(Edge{0,1}) {t.Fatalf("four-incidence edge absent: %+v",r)}
 if r.TotalFaces!=len(faces){t.Fatal("lost source faces")}
}
func TestNoFalseOppositeForRotatedSameWinding(t *testing.T) {
 r,e:=Inspect([]Face{{0,1,2},{1,2,0}});if e!=nil{t.Fatal(e)}
 if len(r.OppositePairs)!=0 {t.Fatalf("same winding misclassified: %+v",r)}
}
func TestDegenerateAndNegativeIDsRejected(t *testing.T) {
 for _,f:=range []Face{{0,0,1},{-1,2,3}} { if _,e:=Inspect([]Face{f});e==nil{t.Fatalf("accepted invalid face %+v",f)} }
}
func TestDisjointFacesNoFalseInterface(t *testing.T) {
 r,e:=Inspect([]Face{{0,1,2},{3,4,5}});if e!=nil{t.Fatal(e)}
 if len(r.OppositePairs)!=0 || len(r.FourFaceEdges)!=0 || r.TotalFaces!=2 {t.Fatalf("bad disjoint classification: %+v",r)}
}
