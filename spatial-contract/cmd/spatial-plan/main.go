// Command spatial-plan reports a machine-verifiable, media-free spatial job admission.
// It is intentionally not a renderer.
package main

import (
 "encoding/json"
 "fmt"
 "os"
 "example.invalid/spatial-contract/contract"
)
func main(){
 if len(os.Args)<2 || len(os.Args)>3 {fmt.Fprintln(os.Stderr,"usage: spatial-plan fixture | plan SCENE.json");os.Exit(2)}
 if os.Args[1]=="fixture" && len(os.Args)==2{
  enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ")
  if e:=enc.Encode(contract.SyntheticFixture());e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}
  return
 }
 if os.Args[1]!="plan" || len(os.Args)!=3{fmt.Fprintln(os.Stderr,"invalid command");os.Exit(2)}
 s,e:=contract.Load(os.Args[2])
 if e!=nil{fmt.Fprintln(os.Stderr,"SPATIAL_ADMISSION_FAIL:",e);os.Exit(1)}
 digest,e:=s.Admission(true)
 if e!=nil{fmt.Fprintln(os.Stderr,"SPATIAL_ADMISSION_FAIL:",e);os.Exit(1)}
 outputs:=make([]map[string]interface{},0,len(s.Outputs))
 for _,v:=range s.Outputs{
  outputs=append(outputs,map[string]interface{}{"id":v.ID,"profile":v.Profile,"channel_count":len(v.Channels),"channel_order":v.Channels,"lfe_policy":v.LFEPolicy,"hrtf":v.HRTF,"render_status":"UNQUALIFIED_UNTIL_BACKEND_PASS"})
 }
 receipt:=map[string]interface{}{
  "schema":"spatial_audio.plan.v1","scene_id":s.ID,"classification":s.Classification,
  "scene_sha256":digest,"world_frame":s.WorldFrame,"sample_rate_hz":s.SampleRateHz,
  "duration_ms":s.DurationMS,"emitters":len(s.Emitters),"outputs":outputs,
  "warning":"SOURCE CONTRACT ONLY: no validated channel mapping, HRTF localization, signal render, Dolby/THX certification or head tracking",
 }
 enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ")
 if e=enc.Encode(receipt);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}
}
