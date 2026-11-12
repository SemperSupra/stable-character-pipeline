package main
// Original synthetic mesh bakeoff consumer; unchanged donor source.
import(
 "fmt"
 "os"
 "github.com/deadsy/sdfx/sdf"
 "github.com/deadsy/sdfx/render"
 "github.com/deadsy/sdfx/vec/v3"
)
func main(){
 if len(os.Args)!=3{panic("usage: sdfx-mesh uniform|octree destination.stl")}
 sphere,e:=sdf.Sphere3D(1);if e!=nil{panic(e)}
 box,e:=sdf.Box3D(v3.Vec{X:2.8,Y:0.5,Z:0.5},0);if e!=nil{panic(e)}
 shape:=sdf.Union3D(sphere,box)
 switch os.Args[1] {
 case "uniform":render.ToSTL(shape,os.Args[2],render.NewMarchingCubesUniform(40))
 case "octree":render.ToSTL(shape,os.Args[2],render.NewMarchingCubesOctree(40))
 default:panic("invalid strategy")
 }
 i,e:=os.Stat(os.Args[2]);if e!=nil||i.Size()<84{panic(fmt.Sprintf("no mesh: %v",e))}
 fmt.Printf("SDFX_MESH_WRITTEN %s %d\n",os.Args[1],i.Size())
}
