package volume
import ("math";"testing")
func tetra()([]V,[]Face){return []V{{0,0,0},{1,0,0},{0,1,0},{0,0,1}},[]Face{{0,2,1},{0,1,3},{0,3,2},{1,2,3}}}
func TestClosedTetraOriginInvariant(t *testing.T) {
 v,f:=tetra()
 for _,o:=range []V{{0,0,0},{12,-7,4},{-1000,3000,-2500}} {
  got,e:=Signed(v,f,o);if e!=nil||math.Abs(got-1.0/6)>1e-9 {t.Fatalf("origin=%+v got=%g err=%v",o,got,e)}
 }
}
func TestReversedWindingReversesSignedVolume(t *testing.T) {
 v,f:=tetra();for i:=range f {f[i].B,f[i].C=f[i].C,f[i].B}
 got,e:=Signed(v,f,V{});if e!=nil||math.Abs(got+1.0/6)>1e-12 {t.Fatalf("got=%g err=%v",got,e)}
}
func TestOpenAndBadWindingReject(t *testing.T) {
 v,f:=tetra()
 if _,e:=Signed(v,f[:3],V{});e==nil{t.Fatal("open surface accepted")}
 f[0].B,f[0].C=f[0].C,f[0].B
 if _,e:=Signed(v,f,V{});e==nil{t.Fatal("inconsistent orientation accepted")}
}
func TestNonfiniteAndInvalidIndexReject(t *testing.T){
 v,f:=tetra();v[1].X=math.NaN()
 if _,e:=Signed(v,f,V{});e==nil{t.Fatal("NaN accepted")}
 v,f=tetra();f[1].C=99
 if _,e:=Signed(v,f,V{});e==nil{t.Fatal("invalid index accepted")}
}
