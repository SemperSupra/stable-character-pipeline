// Command scene exposes the exact same soundtrack contract to creators,
// noninteractive operators and agents. All output is machine-readable JSON.
package main
import (
 "flag"
 "fmt"
 "os"
 "example.invalid/audio-foundry-fixture/scene"
)
func run(args []string)error{
 if len(args)<1{return fmt.Errorf("usage: scene init|plan|render -assets DIR [-manifest FILE] [-out WAV]")}
 switch args[0]{
 case "init":
  f:=flag.NewFlagSet("init",flag.ContinueOnError)
  assets:=f.String("assets","","directory of generated, public synthetic WAV stems")
  if e:=f.Parse(args[1:]);e!=nil{return e}
  if *assets=="" || f.NArg()!=0{return fmt.Errorf("init requires -assets and no extra arguments")}
  m,e:=scene.Example(*assets);if e!=nil{return e}
  if _,e=m.Plan(*assets,false);e!=nil{return e}
  return scene.JSON(m)
 case "plan","render":
  f:=flag.NewFlagSet(args[0],flag.ContinueOnError)
  assets:=f.String("assets","","audio input directory")
  manifest:=f.String("manifest","","scene_audio.v1 JSON file")
  out:=f.String("out","","new output WAV path")
  private:=f.Bool("private-workcell",false,"explicit private-only admission; NEVER on public CI")
  if e:=f.Parse(args[1:]);e!=nil{return e}
  if *assets==""||*manifest==""||f.NArg()!=0{return fmt.Errorf("-assets and -manifest are required")}
  m,e:=scene.Load(*manifest);if e!=nil{return e}
  if args[0]=="plan"{
   if *out!=""{return fmt.Errorf("-out applies only to render")}
   r,e:=m.Plan(*assets,*private);if e!=nil{return e};return scene.JSON(r)
  }
  if *out==""{return fmt.Errorf("render requires -out")}
  r,e:=m.Render(*assets,*out,*private);if e!=nil{return e}
  return scene.JSON(r)
 default:return fmt.Errorf("unknown command %s",args[0])
 }
}
func main(){if e:=run(os.Args[1:]);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}}
