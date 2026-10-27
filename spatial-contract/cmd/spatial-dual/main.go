// spatial-dual is W3a's original-sources fixture and native block plan.
// It composes existing spatial_audio.v1, real-byte AdmitSources and PoseAtFrame;
// it does not synthesize DSP, or claim arbitrary source/track generalization.
package main
import (
 "bufio"
 "encoding/json"
 "errors"
 "fmt"
 "math"
 "os"
 "path/filepath"
 "strconv"
 "example.invalid/spatial-contract/contract"
)

const block=1024
const durationMS=1000
const cls="PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL"

type Track struct {
 ID string `json:"id"`
 Name string `json:"name"`
 SHA256 string `json:"sha256"`
 Category string `json:"category"`
 GainDB float64 `json:"gain_db"`
}
type PlanReceipt struct {
 Schema string `json:"schema"`
 SceneID string `json:"scene_id"`
 SceneSHA256 string `json:"scene_sha256"`
 Classification string `json:"classification"`
 Tracks []Track `json:"tracks"`
 Blocks int `json:"blocks"`
 Frames int `json:"frames"`
 LastBlock int `json:"last_block"`
 Interpolation string `json:"interpolation"`
 RenderStatus string `json:"render_status"`
}
func fixture(dir string)error{
 if err:=os.Mkdir(dir,0700);err!=nil{return err}
 a,err:=contract.WriteOriginalTone(filepath.Join(dir,"robot_a.wav"),durationMS,410)
 if err!=nil{return err}
 b,err:=contract.WriteOriginalTone(filepath.Join(dir,"robot_b.wav"),durationMS,690)
 if err!=nil{return err}
 if a==b{return errors.New("two independent source bytes required")}
 s:=contract.SyntheticFixture()
 s.ID="spatial_dual_emitter_public"
 s.Emitters[0].ID="robot_a"
 s.Emitters[0].AudioAsset="robot_a.wav"
 s.Emitters[0].AssetSHA256=a
 s.Emitters[0].GainDB= -9
 s.Emitters[0].Motion=[]contract.Key{
  {TimeMS:0,Position:contract.Vec3{X:-5,Y:6,Z:0}},
  {TimeMS:500,Position:contract.Vec3{X:5,Y:6,Z:0}},
 }
 s.Emitters=append(s.Emitters,contract.Emitter{
  ID:"robot_b",Category:"mechanical",AudioAsset:"robot_b.wav",
  AssetSHA256:b, GainDB:-12,Directivity:"omni", SpreadDeg:0,
  Motion:[]contract.Key{
   {TimeMS:0,Position:contract.Vec3{X:6,Y:7,Z:0}},
   {TimeMS:500,Position:contract.Vec3{X:-6,Y:7,Z:0}},
  },
 })
 if _,err=s.Admission(true);err!=nil{return err}
 buf,err:=json.MarshalIndent(s,"","  ");if err!=nil{return err}
 f,err:=os.OpenFile(filepath.Join(dir,"scene.json"),os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600);if err!=nil{return err}
 n,e:=f.Write(append(buf,'\n'));ce:=f.Close()
 if e!=nil||ce!=nil||n!=len(buf)+1{return errors.New("fixture source scene incomplete")}
 fmt.Printf("spatial_dual_fixture_CREATED sources=2 real_sha_a=%s real_sha_b=%s\n",a,b)
 return nil
}
func build(s contract.Scene,receipts []contract.AssetReceipt)([]string,PlanReceipt,error){
 if len(s.Emitters)!=2 || len(receipts)!=2{return nil,PlanReceipt{},errors.New("W3a requires exactly two admitted source tracks")}
 if s.Emitters[0].ID!="robot_a" || s.Emitters[1].ID!="robot_b" || s.Emitters[0].AudioAsset==s.Emitters[1].AudioAsset {
  return nil,PlanReceipt{},errors.New("two fixed stable IDs and distinct source files required")
 }
 for i,em:=range s.Emitters{
  if em.Directivity!="omni" || em.SpreadDeg!=0 || em.GainDB>0 || em.GainDB< -40 {
   return nil,PlanReceipt{},errors.New("unqualified source directivity/spread/gain")
  }
  if receipts[i].EmitterID!=em.ID || receipts[i].Name!=em.AudioAsset || receipts[i].SHA256!=em.AssetSHA256 {
   return nil,PlanReceipt{},errors.New("source identity/order receipt does not match")
  }
 }
 has51:=false
 for _,o:=range s.Outputs{if o.Profile=="surround_5_1"{has51=true}}
 if !has51{return nil,PlanReceipt{},errors.New("5.1 target missing")}
 digest,e:=s.Admission(true);if e!=nil{return nil,PlanReceipt{},e}
 frames:=s.DurationMS*48
 lines:=[]string{}
 for start:=0;start<frames;start+=block{
  n:=block;if frames-start<n{n=frames-start}
  pA,e:=contract.PoseAtFrame(s,s.Emitters[0].ID,start)
  if e!=nil{return nil,PlanReceipt{},e}
  pB,e:=contract.PoseAtFrame(s,s.Emitters[1].ID,start)
  if e!=nil{return nil,PlanReceipt{},e}
  ga:=math.Pow(10,s.Emitters[0].GainDB/20)
  gb:=math.Pow(10,s.Emitters[1].GainDB/20)
  if !finite(ga)||!finite(gb)||ga<=0||gb<=0{return nil,PlanReceipt{},errors.New("bad amplitude")}
  lines=append(lines,fmt.Sprintf("%d %d %s %.12f %.12f %.12f %.12f %s %.12f %.12f %.12f %.12f",
   start,n,s.Emitters[0].ID,pA.AzimuthDeg,pA.ElevationDeg,pA.DistanceM,ga,
   s.Emitters[1].ID,pB.AzimuthDeg,pB.ElevationDeg,pB.DistanceM,gb))
 }
 last:=frames%block;if last==0{last=block}
 return lines,PlanReceipt{
  Schema:"spatial_audio.dual_blockplan.v1",SceneID:s.ID,SceneSHA256:digest,Classification:cls,
  Tracks:[]Track{
   {ID:s.Emitters[0].ID,Name:receipts[0].Name,SHA256:receipts[0].SHA256,Category:s.Emitters[0].Category,GainDB:s.Emitters[0].GainDB},
   {ID:s.Emitters[1].ID,Name:receipts[1].Name,SHA256:receipts[1].SHA256,Category:s.Emitters[1].Category,GainDB:s.Emitters[1].GainDB},
  }, Blocks:len(lines),Frames:frames,LastBlock:last,
  Interpolation:"linear_ENU_pose_at_native_block_start",
  RenderStatus:"NOT_RENDERED_YET",
 },nil
}
func finite(x float64)bool{return !math.IsNaN(x)&&!math.IsInf(x,0)}
func plan(scene,sourceDir,newPlan string)error{
 s,e:=contract.Load(scene);if e!=nil{return e}
 if _,e=s.Admission(true);e!=nil{return e}
 a,e:=contract.AdmitSources(s,sourceDir,true);if e!=nil{return e}
 lines,receipt,e:=build(s,a);if e!=nil{return e}
 f,e:=os.OpenFile(newPlan,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600);if e!=nil{return e}
 out:=bufio.NewWriter(f)
 for _,line:=range lines{if _,e=fmt.Fprintln(out,line);e!=nil{break}}
 if e==nil{e=out.Flush()}
 ce:=f.Close();if e==nil{e=ce}
 if e!=nil{os.Remove(newPlan);return e}
 encoder:=json.NewEncoder(os.Stdout);encoder.SetIndent("","  ")
 return encoder.Encode(receipt)
}
func main(){
 var e error
 switch{
 case len(os.Args)==3&&os.Args[1]=="fixture":e=fixture(os.Args[2])
 case len(os.Args)==4&&os.Args[1]=="tone":
  var hz float64;hz,e=strconv.ParseFloat(os.Args[3],64)
  if e==nil{_,e=contract.WriteOriginalTone(os.Args[2],durationMS,hz)}
 case len(os.Args)==5&&os.Args[1]=="plan":e=plan(os.Args[2],os.Args[3],os.Args[4])
 default:fmt.Fprintln(os.Stderr,"usage: spatial-dual fixture NEW_DIR | plan SCENE AUDIO_DIR NEW_PLAN | tone NEW_WAV FREQUENCY_HZ");os.Exit(2)
 }
 if e!=nil{fmt.Fprintln(os.Stderr,"SPATIAL_DUAL_FIRST_FAILURE:",e);os.Exit(1)}
}
