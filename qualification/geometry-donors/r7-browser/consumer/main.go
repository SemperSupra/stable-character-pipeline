package main
// Original public-safe analytic CSG operation using unchanged pinned sdfx.
import(
 "encoding/json"
 "fmt"
 "github.com/deadsy/sdfx/sdf"
 "github.com/deadsy/sdfx/vec/v3"
)
type Sample struct{XYZ [3]float64 `json:"xyz"`;Distance float64 `json:"distance"`}
func main(){
 a,e:=sdf.Sphere3D(1);if e!=nil{panic(e)}
 b,e:=sdf.Box3D(v3.Vec{X:2.8,Y:0.5,Z:0.5},0);if e!=nil{panic(e)}
 union:=sdf.Union3D(a,b)
 _,bad:=sdf.Sphere3D(0)
 points:=[][3]float64{{0,0,0},{1,0,0},{1.5,0,0},{0.6,0.8,0},{0.3,-0.4,0.5},{1.3,0,0},
  {1.6,0,0},{0,0.6,0},{1.3,0.2,0},{0.4,0.25,0.5},{1.8,1.1,0},{0,0,2}}
 samples:=make([]Sample,0,len(points))
 for _,p:=range points{samples=append(samples,Sample{XYZ:p,Distance:union.Evaluate(v3.Vec{X:p[0],Y:p[1],Z:p[2]})})}
 receipt:=struct{Donor string `json:"donor"`;InvalidRejected bool `json:"invalid_rejected"`;Samples []Sample `json:"samples"`}{ "sdfx",bad!=nil,samples }
 payload,e:=json.Marshal(receipt);if e!=nil{panic(e)}
 fmt.Println("WASM_RESULT="+string(payload))
}
