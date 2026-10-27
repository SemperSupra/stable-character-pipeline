// spatial-admit is a three-audience operator/agent entrypoint:
// create one rights-clean real WAV scene, then independently verify its bytes
// and sample-aligned spatial poses. No rendering or licensed codec claims.
package main

import (
 "encoding/json"
 "errors"
 "fmt"
 "os"
 "path/filepath"
 "example.invalid/spatial-contract/contract"
)
type Receipt struct {
 Schema string `json:"schema"`
 Classification string `json:"classification"`
 SceneSHA256 string `json:"scene_sha256"`
 SceneID string `json:"scene_id"`
 Sources []contract.AssetReceipt `json:"sources"`
 PoseStart contract.RelativePose `json:"pose_start"`
 PoseMid contract.RelativePose `json:"pose_mid"`
 Status string `json:"status"`
}
func fixture(root string)error{
 if root==""{return errors.New("missing destination")}
 if e:=os.Mkdir(root,0700);e!=nil{return e}
 path:=filepath.Join(root,"synthetic.wav")
 hash,e:=contract.WriteOriginalSine(path,1000);if e!=nil{return e}
 s:=contract.SyntheticFixture()
 s.Emitters[0].AssetSHA256=hash
 if _,e=s.Admission(true);e!=nil{return e}
 b,e:=json.MarshalIndent(s,"","  ");if e!=nil{return e}
 f,e:=os.OpenFile(filepath.Join(root,"scene.json"),os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if e!=nil{return e}
 if _,e=f.Write(append(b,'\n'));e!=nil{f.Close();return e}
 if e=f.Close();e!=nil{return e}
 fmt.Println("spatial_original_real_source_CREATED class=PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL sha256="+hash)
 return nil
}
func verify(scenePath,root string)error{
 s,e:=contract.Load(scenePath);if e!=nil{return e}
 digest,e:=s.Admission(true);if e!=nil{return e}
 assets,e:=contract.AdmitSources(s,root,true);if e!=nil{return e}
 if len(s.Emitters)!=1{return errors.New("fixture CLI expects one original emitter; library supports multiple")}
 start,e:=contract.PoseAtFrame(s,s.Emitters[0].ID,0);if e!=nil{return e}
 mid,e:=contract.PoseAtFrame(s,s.Emitters[0].ID,s.DurationMS*48/2);if e!=nil{return e}
 output:=Receipt{Schema:"spatial_audio.custody_geometry_receipt.v1",
  Classification:s.Classification,SceneSHA256:digest,SceneID:s.ID,
  Sources:assets,PoseStart:start,PoseMid:mid,
  Status:"REAL_WAV_CUSTODY_AND_GEOMETRY_PASS_RENDERER_NOT_YET_CONNECTED"}
 enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ")
 return enc.Encode(output)
}
func main(){
 var e error
 switch{
 case len(os.Args)==3&&os.Args[1]=="fixture":e=fixture(os.Args[2])
 case len(os.Args)==4&&os.Args[1]=="verify":e=verify(os.Args[2],os.Args[3])
 default:fmt.Fprintln(os.Stderr,"usage: spatial-admit fixture NEW_DIR | verify SCENE.json AUDIO_DIR");os.Exit(2)
 }
 if e!=nil{fmt.Fprintln(os.Stderr,"SPATIAL_SOURCE_FIRST_FAILURE:",e);os.Exit(1)}
}
