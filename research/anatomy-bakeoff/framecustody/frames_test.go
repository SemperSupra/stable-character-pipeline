package framecustody

import (
 "math"
 "strings"
 "testing"
)
const h="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
func fixture()(Graph,[4][4]float64){
 // Synthetic mm/Z-up reference to m/Y-up character. This is a known
 // mathematical axis conversion, NOT a declared actual BP3D/HRA mapping.
 a:=Frame{ID:"REFERENCE_SYNTH",Dataset:"synthetic",Version:"1",SourceSHA256:h,
  Units:"mm",UnitEvidenceSHA256:h,Axes:"Z_UP",AxisEvidenceSHA256:h,Laterality:"X_POS_LEFT"}
 b:=Frame{ID:"CANONICAL_SYNTH",Dataset:"synthetic",Version:"1",SourceSHA256:h,
  Units:"m",UnitEvidenceSHA256:h,Axes:"Y_UP",AxisEvidenceSHA256:h,Laterality:"X_POS_LEFT"}
 m:=[4][4]float64{{.001,0,0,0},{0,0,.001,0},{0,-.001,0,0},{0,0,0,1}}
 g:=Graph{Schema:Schema,Frames:[]Frame{a,b},Edges:[]Edge{
  {From:a.ID,To:b.ID,Kind:"UNIT_AXIS_CONVERSION",Matrix:m,Review:"SOURCE_VERIFIED",SourceEvidenceSHA256:h},
 }}
 return g,m
}
func TestDeclaredSourceAxisAndUnitConversion(t *testing.T){
 g,_:=fixture()
 r,e:=Resolve(g,"REFERENCE_SYNTH","CANONICAL_SYNTH")
 if e!=nil||r.Status!="PROVENANCE_GATED_COORDINATE_TRANSFORM_ONLY"{t.Fatal(r,e)}
 v:=Apply(r.Matrix,Point{X:100,Y:200,Z:1200})
 if math.Abs(v.X-.1)>1e-10||math.Abs(v.Y-1.2)>1e-10||math.Abs(v.Z+.2)>1e-10{
  t.Fatalf("proper Z-up mm to Y-up m conversion wrong: %+v",v)
 }
 if len(r.ProvenanceDigest)!=64{t.Fatal("missing digest")}
}
func TestUnknownUnitsAndUnreviewedAtlasNeverAutoInfer(t *testing.T){
 g,_:=fixture()
 g.Frames[0].Units="UNKNOWN"
 if _,e:=Resolve(g,"REFERENCE_SYNTH","CANONICAL_SYNTH");e==nil{t.Fatal("unknown reference units inferred")}
 g,_=fixture()
 g.Frames[0].UnitEvidenceSHA256=""
 if _,e:=Resolve(g,"REFERENCE_SYNTH","CANONICAL_SYNTH");e==nil{t.Fatal("unattributed unit convention admitted")}
 g,_=fixture()
 g.Edges[0].Kind="CROSS_ATLAS_REGISTRATION"
 g.Edges[0].Review="PROPOSED"
 if _,e:=Resolve(g,"REFERENCE_SYNTH","CANONICAL_SYNTH");e==nil{t.Fatal("unreviewed inter-atlas transform admitted")}
 g.Edges[0].Review="SOURCE_VERIFIED"
 if _,e:=Resolve(g,"REFERENCE_SYNTH","CANONICAL_SYNTH");e==nil{t.Fatal("no landmark receipt accepted")}
}
func TestRejectMirrorWrongScaleAndMultiplePaths(t *testing.T){
 g,_:=fixture()
 g.Edges[0].Matrix[0][0]*=-1
 if _,e:=Resolve(g,"REFERENCE_SYNTH","CANONICAL_SYNTH");e==nil||!strings.Contains(e.Error(),"MIRRORED"){t.Fatal("mirror accepted",e)}
 g,_=fixture()
 g.Edges[0].Matrix[0][0]=1
 if _,e:=Resolve(g,"REFERENCE_SYNTH","CANONICAL_SYNTH");e==nil{t.Fatal("implicit mm/m unit confusion accepted")}
 g,_=fixture()
 c:=Frame{ID:"INTERMEDIATE_SYNTH",Dataset:"synthetic",Version:"1",SourceSHA256:h,
  Units:"mm",UnitEvidenceSHA256:h,Axes:"Z_UP",AxisEvidenceSHA256:h,Laterality:"X_POS_LEFT"}
 g.Frames=append(g.Frames,c)
 g.Edges=append(g.Edges,Edge{From:"REFERENCE_SYNTH",To:c.ID,Kind:"UNIT_AXIS_CONVERSION",
  Matrix:identity(),Review:"SOURCE_VERIFIED",SourceEvidenceSHA256:h})
 g.Edges=append(g.Edges,Edge{From:c.ID,To:"CANONICAL_SYNTH",Kind:"UNIT_AXIS_CONVERSION",
  Matrix:g.Edges[0].Matrix,Review:"SOURCE_VERIFIED",SourceEvidenceSHA256:h})
 if _,e:=Resolve(g,"REFERENCE_SYNTH","CANONICAL_SYNTH");e==nil||!strings.Contains(e.Error(),"AMBIGUOUS"){t.Fatal("multiple sources silently selected",e)}
}
func TestSameReferenceCannotLaunderDifferentDonor(t *testing.T){
 g,_:=fixture()
 g.Frames[1].Dataset="other_donor"
 g.Edges[0].Kind="SAME_ATLAS_REFERENCE"
 if _,e:=Resolve(g,"REFERENCE_SYNTH","CANONICAL_SYNTH");e==nil{t.Fatal("cross-person reference laundered as identical")}
}
