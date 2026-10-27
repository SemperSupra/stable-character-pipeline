package main
import (
 "encoding/json"
 "flag"
 "fmt"
 "os"

 "github.com/SemperSupra/stable-character-pipeline/mmd/roadmap/envelope/g10bridge"
)
func main(){
 var paths g10bridge.Paths
 flag.StringVar(&paths.Model,"pmx","","actual original G10a PMX")
 flag.StringVar(&paths.Motion,"vmd","","actual original G10a VMD")
 flag.StringVar(&paths.FixtureReceipt,"fixture","","original G10a native file receipt")
 flag.StringVar(&paths.IKGLB,"ik-glb","","original G10a real IK GLB")
 flag.StringVar(&paths.NoIKGLB,"fk-glb","","original G10a no IK GLB")
 flag.StringVar(&paths.DirectReceipt,"direct","","original G10b independent IK numeric receipt")
 flag.StringVar(&paths.BlenderReceipt,"blender","","original G10c native Blender IK numeric receipt")
 flag.StringVar(&paths.ParityReceipt,"parity","","original G10d cross-engine parity receipt")
 out:=flag.String("out","","new JSON output; never overwrites")
 flag.Parse()
 if *out==""{fmt.Fprintln(os.Stderr,"missing -out");os.Exit(4)}
 f,err:=os.OpenFile(*out,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil {fmt.Fprintln(os.Stderr,"output must be new:",err);os.Exit(4)}
 defer f.Close()
 r,err:=g10bridge.Build(paths)
 if err!=nil {
  fmt.Fprintln(os.Stderr,"EVIDENCE_BINDING_FAILED:",err)
  f.Close()
  os.Remove(*out)
  os.Exit(2)
 }
 encoder:=json.NewEncoder(f);encoder.SetIndent("","  ")
 if err:=encoder.Encode(r);err!=nil {fmt.Fprintln(os.Stderr,err);os.Exit(4)}
}
