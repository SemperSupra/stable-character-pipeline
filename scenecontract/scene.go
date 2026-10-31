package scenecontract
import(
 "bytes"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "regexp"
 "strings"
)
const Schema="scp.scene.v1"
var revisionRE=regexp.MustCompile("^[a-f0-9]{40}$")
var shaRE=regexp.MustCompile("^sha256:[a-f0-9]{64}$")
var actorIDRE=regexp.MustCompile("^[A-Za-z][A-Za-z0-9_-]{0,63}$")
var cameraIDRE=regexp.MustCompile("^[a-z][a-z0-9_-]{0,63}$")
type Actor struct {
 ID string `json:"id"`
 AssetDigest string `json:"asset_digest"`
 SourceClass string `json:"source_class"`
}
type Scene struct {
 Schema string `json:"schema"`
 Revision string `json:"revision"`
 Action string `json:"action"`
 FPS int `json:"fps"`
 Frames int `json:"frames"`
 Actors []Actor `json:"actors"`
 Cameras []string `json:"cameras"`
}
type Decision struct {
 Status string `json:"status"`
 Code string `json:"code"`
 Revision string `json:"revision,omitempty"`
}
func walk(d *json.Decoder)error{
 token,err:=d.Token();if err!=nil{return err}
 x,ok:=token.(json.Delim);if !ok{return nil}
 switch x{
 case '{':
  seen:=map[string]struct{}{}
  for d.More(){
   k,err:=d.Token();if err!=nil{return err}
   key,ok:=k.(string);if !ok{return errors.New("nonstring key")}
   if _,yes:=seen[key];yes{return fmt.Errorf("duplicate JSON key: %s",key)}
   seen[key]=struct{}{}
   if err:=walk(d);err!=nil{return err}
  }
  _,err=d.Token();return err
 case '[':
  for d.More(){if err:=walk(d);err!=nil{return err}}
  _,err=d.Token();return err
 default:return fmt.Errorf("bad delimiter: %q",x)
 }
}
func Decode(r io.Reader)(Scene,error){
 raw,err:=io.ReadAll(io.LimitReader(r,(1<<20)+1))
 if err!=nil{return Scene{},err}
 if len(raw)>(1<<20){return Scene{},errors.New("payload exceeds 1MiB")}
 a:=json.NewDecoder(bytes.NewReader(raw))
 if err:=walk(a);err!=nil{return Scene{},err}
 if _,err:=a.Token();err!=io.EOF{return Scene{},errors.New("trailing JSON")}
 b:=json.NewDecoder(bytes.NewReader(raw));b.DisallowUnknownFields()
 var s Scene
 if err:=b.Decode(&s);err!=nil{return Scene{},err}
 return s,nil
}
func Validate(s Scene)Decision{
 fail:=func(code string)Decision{return Decision{Status:"FAIL",Code:code,Revision:s.Revision}}
 if s.Schema!=Schema{return fail("SCHEMA_MISMATCH")}
 if !revisionRE.MatchString(s.Revision){return fail("INVALID_REVISION")}
 if s.Action!="walk_approach"&&s.Action!="walk_outward"{return fail("INVALID_ACTION")}
 if s.FPS<1||s.FPS>120||s.Frames<2||s.Frames>7200{return fail("INVALID_CLOCK")}
 if len(s.Actors)!=2{return fail("EXACTLY_TWO_ACTORS_REQUIRED")}
 if len(s.Cameras)<2||len(s.Cameras)>4{return fail("INVALID_CAMERA_COUNT")}
 ids:=map[string]bool{}
 for _,a:=range s.Actors{
  if !actorIDRE.MatchString(a.ID){return fail("INVALID_ACTOR_ID")}
  canonical:=strings.ToLower(a.ID)
  if ids[canonical]{return fail("DUPLICATE_ACTOR")}
  ids[canonical]=true
  if !shaRE.MatchString(a.AssetDigest){return fail("INVALID_ASSET_DIGEST")}
  if a.SourceClass!="public-synthetic"&&a.SourceClass!="protected-product"{return fail("INVALID_SOURCE_CLASS")}
 }
 cameras:=map[string]bool{}
 for _,c:=range s.Cameras{
  if !cameraIDRE.MatchString(c){return fail("INVALID_CAMERA_ID")}
  if cameras[c]{return fail("DUPLICATE_CAMERA")}
  cameras[c]=true
 }
 return Decision{Status:"PASS",Code:"STRUCTURAL_CONTRACT_ONLY",Revision:s.Revision}
}
func Evaluate(r io.Reader)(Decision,error){
 scene,err:=Decode(r)
 if err!=nil{return Decision{Status:"FAIL",Code:"INVALID_JSON"},err}
 return Validate(scene),nil
}
func ReadAllSafe(r io.Reader)([]byte,error){
 b,err:=io.ReadAll(io.LimitReader(r,(1<<20)+1))
 if len(b)>(1<<20){return nil,errors.New("too large")}
 return b,err
}
func IsPublicSynthetic(s Scene)bool{
 for _,a:=range s.Actors{if strings.Compare(a.SourceClass,"public-synthetic")!=0{return false}}
 return true
}
