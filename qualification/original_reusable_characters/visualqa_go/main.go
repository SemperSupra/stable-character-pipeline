// Source-specific original-only video clothing-color visibility falsifier.
// Pixel visibility is NOT human pose, gait, face quality or identity acceptance.
package main

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "os/exec"
)

type Counts struct { Pink int `json:"aster_coral_px"`; Teal int `json:"juniper_teal_px"` }
type View struct {
 Path string `json:"path"`
 SHA256 string `json:"video_sha256"`
 Width int `json:"width"`; Height int `json:"height"`
 Frames int `json:"frames"`
 Initial Counts `json:"initial"`
 Minimum Counts `json:"minimum"`
 BelowTwentyPercent Counts `json:"frames_below_20_percent_initial"`
 Samples []Counts `json:"all_frame_counts"`
 Status string `json:"status"`
}
type Report struct {
 Schema string `json:"schema"`
 SourceClass string `json:"source_class"`
 Front View `json:"front"`; Oblique View `json:"oblique"`
 JointScience string `json:"joint_contact_anatomy_acceptance"`
 Verdict string `json:"source_specific_visibility_verdict"`
}
func classify(rgb []byte) Counts {
 v:=Counts{}
 for i:=0;i+2<len(rgb);i+=3 {
  r,g,b:=int(rgb[i]),int(rgb[i+1]),int(rgb[i+2])
  if r*100>g*123 && r*100>b*110 && r>60 && g>35 {v.Pink++}
  if g*100>r*122 && b*100>r*125 && b*100>g*83 && g>60 {v.Teal++}
 }
 return v
}
func assess(samples []Counts) (Counts,Counts,string,error) {
 if len(samples)!=72{return Counts{},Counts{},"INVALID",fmt.Errorf("EXPECTED_72_FRAMES_%d",len(samples))}
 first:=samples[0]
 if first.Pink<30||first.Teal<30{return first,Counts{},"INVALID",errors.New("INSUFFICIENT_INITIAL_COLOR_WITNESS")}
 min:=first;low:=Counts{}
 for _,s:=range samples {
  if s.Pink<min.Pink{min.Pink=s.Pink}
  if s.Teal<min.Teal{min.Teal=s.Teal}
  if s.Pink*5<first.Pink{low.Pink++}
  if s.Teal*5<first.Teal{low.Teal++}
 }
 status:="PASS_COLOR_VISIBILITY_PROXY_ONLY"
 if low.Pink>0||low.Teal>0{status="FAIL_COLOR_OCCLUSION_PROXY"}
 return min,low,status,nil
}
func one(path string)(View,error){
 r:=View{Path:path}
 input,err:=os.ReadFile(path);if err!=nil{return r,err}
 digest:=sha256.Sum256(input);r.SHA256=hex.EncodeToString(digest[:])
 type Stream struct{ Width int `json:"width"`; Height int `json:"height"` }
 var probe struct{ Streams []Stream `json:"streams"` }
 out,err:=exec.Command("ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","json",path).Output()
 if err!=nil{return r,fmt.Errorf("FFPROBE:%w",err)}
 if err=json.Unmarshal(out,&probe);err!=nil{return r,err}
 if len(probe.Streams)!=1{return r,errors.New("EXPECTED_ONE_VIDEO_STREAM")}
 r.Width,r.Height=probe.Streams[0].Width,probe.Streams[0].Height
 if r.Width<=0||r.Height<=0||r.Width*r.Height>1920*1080{return r,errors.New("INVALID_OR_UNBOUNDED_DIMENSIONS")}
 raw,err:=exec.Command("ffmpeg","-hide_banner","-loglevel","error","-i",path,"-an","-pix_fmt","rgb24","-f","rawvideo","pipe:1").Output()
 if err!=nil{return r,fmt.Errorf("FFMPEG:%w",err)}
 bytesPer:=r.Width*r.Height*3
 if len(raw)%bytesPer!=0{return r,errors.New("TRUNCATED_RAW_FRAMES")}
 r.Frames=len(raw)/bytesPer
 samples:=make([]Counts,0,r.Frames)
 for i:=0;i<r.Frames;i++{samples=append(samples,classify(raw[i*bytesPer:(i+1)*bytesPer]))}
 r.Samples=samples
 if r.Frames>0{r.Initial=samples[0]}
 r.Minimum,r.BelowTwentyPercent,r.Status,err=assess(samples)
 return r,err
}
func main(){
 front:=flag.String("front","","source-original front MP4")
 oblique:=flag.String("oblique","","source-original oblique MP4")
 receipt:=flag.String("receipt","","new JSON receipt path")
 flag.Parse()
 if *front==""||*oblique==""||*receipt==""||*front==*oblique{panic("DISTINCT_INPUTS_REQUIRED")}
 a,err:=one(*front);if err!=nil{panic(err)}
 b,err:=one(*oblique);if err!=nil{panic(err)}
 verdict:="PASS_TWO_VIEW_CLOTHING_VISIBILITY_PROXY_ONLY"
 if a.Status!="PASS_COLOR_VISIBILITY_PROXY_ONLY"||b.Status!="PASS_COLOR_VISIBILITY_PROXY_ONLY"{verdict="FAIL_AT_LEAST_ONE_VIEW_OCCLUSION_PROXY"}
 r:=Report{Schema:"scp.r009.original_humanization_color_visibility.v1",SourceClass:"ORIGINAL_SELF_AUTHORED_SYNTHETIC",Front:a,Oblique:b,JointScience:"NOT_EVALUATED",Verdict:verdict}
 payload,err:=json.MarshalIndent(r,"","  ");if err!=nil{panic(err)}
 if err=os.WriteFile(*receipt,append(payload,'
'),0644);err!=nil{panic(err)}
 fmt.Println(verdict,"front",a.Status,"oblique",b.Status)
}
