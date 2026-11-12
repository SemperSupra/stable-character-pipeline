// Original public-safe clean-consumer fixture. No donor source is copied.
package main

import (
    "encoding/json"
    "fmt"
    "os"

    "github.com/soypat/geometry/ms3"
    "github.com/soypat/gsdf"
    "github.com/soypat/gsdf/gleval"
)
type Entry struct { ID string `json:"id"`; XYZ [3]float64 `json:"xyz"`; Distance float64 `json:"distance"` }
type Result struct { Donor string `json:"donor"`; Cases []Entry `json:"cases"`; InvalidRejected bool `json:"invalid_rejected"` }
func main() {
    var builder gsdf.Builder
    if err:=builder.SetFlags(gsdf.FlagNoShaderBuffers);err!=nil{panic(err)}
    shape:=builder.Union(builder.NewSphere(1),builder.NewBox(2.8,0.5,0.5,0))
    if err:=builder.Err();err!=nil{panic(err)}
    cpu,err:=gleval.NewCPUSDF3(shape)
    if err!=nil{panic(err)}
    samples := [][3]float64{
        {0,0,0},{1,0,0},{1.5,0,0},{0.6,0.8,0},{0.3,-0.4,0.5},{1.3,0,0},
        {1.6,0,0},{0,0.6,0},{1.3,0.2,0},{0.4,0.25,0.5},{1.8,1.1,0},{0,0,2},
    }
    positions:=make([]ms3.Vec,len(samples))
    for i,p:=range samples{positions[i]=ms3.Vec{X:float32(p[0]),Y:float32(p[1]),Z:float32(p[2])}}
    distances:=make([]float32,len(samples))
    if err:=cpu.Evaluate(positions,distances,nil);err!=nil{panic(err)}
    var invalid gsdf.Builder
    if err:=invalid.SetFlags(gsdf.FlagNoDimensionPanic|gsdf.FlagNoShaderBuffers);err!=nil{panic(err)}
    invalid.NewSphere(0)
    result:=Result{Donor:"gsdf",InvalidRejected:invalid.Err()!=nil}
    for i,p:=range samples{
        result.Cases=append(result.Cases,Entry{
            ID:fmt.Sprintf("p%02d",i),XYZ:p,Distance:float64(distances[i]),
        })
    }
    enc:=json.NewEncoder(os.Stdout)
    enc.SetIndent("","  ")
    if err:=enc.Encode(result);err!=nil{panic(err)}
}
