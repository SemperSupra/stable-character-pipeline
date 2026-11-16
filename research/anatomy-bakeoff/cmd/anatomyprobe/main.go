package main
import (
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "example.org/scp/anatomy-bakeoff"
)
func emit(v any){enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ");_ = enc.Encode(v)}
func fail(code string,err error){emit(map[string]any{"status":"FAIL","code":code,"message":err.Error()});os.Exit(2)}
func main(){
 if len(os.Args)<2{fmt.Fprintln(os.Stderr,"Usage: anatomyprobe <describe|inspect|toggle>");os.Exit(2)}
 switch os.Args[1]{
 case "describe":
  emit(map[string]any{"name":"scp.anatomy.synthetic.contract.v1","commands":[]string{"describe","inspect","toggle --system circulatory --visible=false"},"schema":anatomy.Schema,"systems":anatomy.Systems,"locales":anatomy.Locales,"authority":"synthetic-only research, not human anatomical or physics qualification","side_effects":"none outside stdout JSON","exit_codes":map[string]string{"0":"success","2":"invalid command/source/precondition"}})
 case "inspect":
  s:=anatomy.SyntheticScene();if e:=anatomy.Validate(s);e!=nil{fail("INVALID_SCENE",e)}
  hash,_:=anatomy.PhysicsDigest(s);emit(map[string]any{"status":"PASS_NARROW","schema":anatomy.Schema,"scene":s,"physics_sha256":hash,"visible_ids":anatomy.VisibleIDs(s)})
 case "toggle":
  flags:=flag.NewFlagSet("toggle",flag.ContinueOnError)
  system:=flags.String("system","","anatomical system");visible:=flags.Bool("visible",true,"render layer visibility")
  if e:=flags.Parse(os.Args[2:]);e!=nil{fail("INVALID_ARGS",e)}
  out,receipt,e:=anatomy.SetSystemVisibility(anatomy.SyntheticScene(),*system,*visible)
  if e!=nil{fail("INVALID_ACTION",e)};emit(map[string]any{"receipt":receipt,"view":out.View})
 default:fail("UNKNOWN_COMMAND",fmt.Errorf("unknown command %q",os.Args[1]))
 }
}
