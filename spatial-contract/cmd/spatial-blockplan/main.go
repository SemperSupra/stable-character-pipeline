// Command spatial-blockplan turns an admitted spatial_audio.v1 source into
// one sample-clock block contract for the native upstream spatial renderer.
package main

import (
 "bufio"
 "encoding/json"
 "fmt"
 "os"
 "strconv"
 "example.invalid/spatial-contract/contract"
)

const nativeBlock=1024
type Receipt struct{
 Schema string `json:"schema"`
 SceneSHA256 string `json:"scene_sha256"`
 SourceSHA256 string `json:"source_sha256"`
 SourceName string `json:"source_name"`
 Blocks int `json:"blocks"`
 SampleFrames int `json:"sample_frames"`
 LastBlockLength int `json:"last_block_length"`
 Status string `json:"status"`
}
func plan(sceneFile,audioRoot,dest string)error{
 s,e:=contract.Load(sceneFile);if e!=nil{return e}
 if _,e=s.Admission(true);e!=nil{return e}
 if len(s.Emitters)!=1{return fmt.Errorf("native W2 supports one emitter; got %d",len(s.Emitters))}
 if s.Emitters[0].Directivity!="omni"||s.Emitters[0].SpreadDeg!=0 {
  return fmt.Errorf("native W2 directivity/spread unsupported")
 }
 has5,hasB:=false,false
 for _,v:=range s.Outputs {
  if v.Profile=="surround_5_1"{has5=true}
  if v.Profile=="binaural"{hasB=v.HRTF=="builtin_mit_test"}
 }
 if !has5||!hasB{return fmt.Errorf("qualified native output targets 5.1 and builtin-MIT binaural required")}
 assets,e:=contract.AdmitSources(s,audioRoot,true);if e!=nil{return e}
 sceneHash,e:=s.Admission(true);if e!=nil{return e}
 out,e:=os.OpenFile(dest,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600);if e!=nil{return e}
 writer:=bufio.NewWriter(out)
 frames:=s.DurationMS*48;blocks:=0;last:=0
 for start:=0;start<frames;start+=nativeBlock{
  n:=nativeBlock;if frames-start<n{n=frames-start}
  pose,err:=contract.PoseAtFrame(s,s.Emitters[0].ID,start)
  if err!=nil{out.Close();os.Remove(dest);return err}
  // Intentional *block-boundary* automation. Within-block continuous
  // interpolation has not been validated by the native renderer yet.
  _,e=fmt.Fprintf(writer,"%d %d %.12f %.12f %.12f\n",
   start,n,pose.AzimuthDeg,pose.ElevationDeg,pose.DistanceM)
  if e!=nil{out.Close();os.Remove(dest);return e}
  last=n;blocks++
 }
 if e=writer.Flush();e!=nil{out.Close();os.Remove(dest);return e}
 if e=out.Close();e!=nil{os.Remove(dest);return e}
 r:=Receipt{Schema:"spatial_audio.native_blockplan.v1",SceneSHA256:sceneHash,
  SourceSHA256:assets[0].SHA256,SourceName:assets[0].Name,
  Blocks:blocks,SampleFrames:frames,LastBlockLength:last,
  Status:"REAL_SOURCE_ADMITTED_BLOCK_AUTOMATION_NOT_PER_SAMPLE"}
 j:=json.NewEncoder(os.Stdout);j.SetIndent("","  ")
 return j.Encode(r)
}
func main(){
 if len(os.Args)!=5||os.Args[1]!="plan"{
  fmt.Fprintln(os.Stderr,"usage: spatial-blockplan plan SCENE.json AUDIO_ROOT NEW_PLAN.tsv");os.Exit(2)
 }
 if e:=plan(os.Args[2],os.Args[3],os.Args[4]);e!=nil{
  fmt.Fprintln(os.Stderr,"SPATIAL_BLOCKPLAN_FIRST_FAILURE:",strconv.Quote(e.Error()));os.Exit(1)
 }
}
