package main
// Original synthetic CPU flat-meshing consumer; unchanged donor source.
import(
 "fmt"
 "os"
 "github.com/soypat/gsdf"
 "github.com/soypat/gsdf/gsdfaux"
)
func main(){
 if len(os.Args)!=2{panic("usage: gsdf-mesh destination.stl")}
 var b gsdf.Builder
 if err:=b.SetFlags(gsdf.FlagNoShaderBuffers|gsdf.FlagNoDimensionPanic);err!=nil{panic(err)}
 shape:=b.Union(b.NewSphere(1),b.NewBox(2.8,0.5,0.5,0))
 if err:=b.Err();err!=nil{panic(err)}
 file,e:=os.Create(os.Args[1]);if e!=nil{panic(e)}
 e=gsdfaux.RenderShader3D(shape,gsdfaux.RenderConfig{STLOutput:file,Resolution:0.080,UseGPU:false,Silent:true,ParallelCPU:2})
 if closeErr:=file.Close();e==nil{e=closeErr}
 if e!=nil{panic(e)}
 i,e:=os.Stat(os.Args[1]);if e!=nil||i.Size()<84{panic(fmt.Sprintf("no mesh: %v",e))}
 fmt.Printf("GSDF_MESH_WRITTEN %d\n",i.Size())
}
