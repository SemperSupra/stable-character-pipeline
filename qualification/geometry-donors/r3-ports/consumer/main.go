package main
// Original public-safe native portability consumer; no donor source copied.
import(
 "encoding/json"
 "os"
 "fmt"
 "github.com/deadsy/sdfx/sdf"
 "github.com/deadsy/sdfx/vec/v3"
)
type Point struct{ ID string `json:"id"`; XYZ [3]float64 `json:"xyz"`; Value float64 `json:"value"` }
type Output struct{ Donor string `json:"donor"`; InvalidRejected bool `json:"invalid_rejected"`; Points []Point `json:"points"` }
func main(){
 a,e:=sdf.Sphere3D(1);if e!=nil{panic(e)}
 b,e:=sdf.Box3D(v3.Vec{X:2.8,Y:0.5,Z:0.5},0);if e!=nil{panic(e)}
 u:=sdf.Union3D(a,b)
 _,bad:=sdf.Sphere3D(0)
 samples:=[][3]float64{
 {0,0,0},{1,0,0},{1.5,0,0},{0.6,0.8,0},{0.3,-0.4,0.5},{1.3,0,0},
 {1.6,0,0},{0,0.6,0},{1.3,0.2,0},{0.4,0.25,0.5},{1.8,1.1,0},{0,0,2},
 }
 out:=Output{Donor:"sdfx",InvalidRejected:bad!=nil}
 for i,p:=range samples{
  out.Points=append(out.Points,Point{ID:fmt.Sprintf("p%02d",i),XYZ:p,Value:u.Evaluate(v3.Vec{X:p[0],Y:p[1],Z:p[2]})})
 }
 enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ");if e:=enc.Encode(out);e!=nil{panic(e)}
}
