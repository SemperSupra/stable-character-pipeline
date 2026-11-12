// Original public-safe clean-consumer fixture. No donor source is copied.
package main

import (
    "encoding/json"
    "fmt"
    "os"
    "github.com/deadsy/sdfx/sdf"
    "github.com/deadsy/sdfx/vec/v3"
)
type Entry struct { ID string `json:"id"`; XYZ [3]float64 `json:"xyz"`; Distance float64 `json:"distance"` }
type Result struct { Donor string `json:"donor"`; Cases []Entry `json:"cases"`; InvalidRejected bool `json:"invalid_rejected"` }
func main() {
    s, err := sdf.Sphere3D(1)
    if err != nil { panic(err) }
    b, err := sdf.Box3D(v3.Vec{X:2.8,Y:0.5,Z:0.5},0)
    if err != nil { panic(err) }
    u := sdf.Union3D(s,b)
    samples := [][3]float64{
        {0,0,0},{1,0,0},{1.5,0,0},{0.6,0.8,0},{0.3,-0.4,0.5},{1.3,0,0},
        {1.6,0,0},{0,0.6,0},{1.3,0.2,0},{0.4,0.25,0.5},{1.8,1.1,0},{0,0,2},
    }
    result := Result{Donor:"sdfx"}
    _, negativeErr := sdf.Sphere3D(0)
    result.InvalidRejected = negativeErr != nil
    for i, p := range samples {
        result.Cases = append(result.Cases,Entry{
            ID:fmt.Sprintf("p%02d",i), XYZ:p,
            Distance:u.Evaluate(v3.Vec{X:p[0],Y:p[1],Z:p[2]}),
        })
    }
    enc:=json.NewEncoder(os.Stdout)
    enc.SetIndent("","  ")
    if err:=enc.Encode(result);err!=nil{panic(err)}
}
