// Original-only R009 two-camera visibility qualification. Color != human gait or anatomical truth.
package main

import (
 "bytes"
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "os/exec"
 "time"
)

const ( width=640; height=360; frames=72; minPixels=500 )
var pinned=map[string]string{
 "before_front":"3cbf7a3e3b7833a9961624132f6d660122f2b48ec217be59a65512f334a91b57",
 "before_oblique":"3da984b1f1f39c48058ca666fedf918771f7d312423f6a3cbe2fd4e41ab04b13",
 "after_front":"0262143935aca0580bca9035b019868fd6b3644da88efe5cb846febe8dbae36c",
 "after_oblique":"7dd7246dacd15260c794507db2ccd507dc790a7f334bde8cab0421e2e07648ea",
}

type Counts struct { Teal int `json:"teal_pixels"`; Pink int `json:"pink_pixels"` }
type Video struct {
 SHA256 string `json:"sha256"`
 Frames int `json:"frames"`
 MinimumTeal int `json:"min_teal_pixels"`
 MinimumPink int `json:"min_pink_pixels"`
 BothAbove500 int `json:"both_at_least_500_pixels"`
 Counts []Counts `json:"per_frame"`
}
type Receipt struct {
 Schema string `json:"schema"`
 Status string `json:"status"`
 Before map[string]Video `json:"before"`
 After map[string]Video `json:"after"`
 VisibilityOnly bool `json:"visibility_only"`
 HumanGait string `json:"human_gait"`
 PhysicalContact string `json:"physical_contact"`
 ProductAccepted bool `json:"product_accepted"`
}

// Original-authored jacket color masks; never infer shape, face, contact or physiology.
func countPixels(rgb []byte) Counts {
 c:=Counts{}
 for i:=0;i+2<len(rgb);i+=3{
  r,g,b:=int(rgb[i]),int(rgb[i+1]),int(rgb[i+2])
  if g-r>25 && b-r>20 && g>60 && b>65 {c.Teal++}
  if r-g>27 && r-b>17 && g>35 && r>95 {c.Pink++}
 }
 return c
}
func assertSHA(path,want string)error{
 f,e:=os.Open(path);if e!=nil{return e};defer f.Close()
 h:=sha256.New();if _,e=io.Copy(h,f);e!=nil{return e}
 got:=hex.EncodeToString(h.Sum(nil))
 if got!=want{return fmt.Errorf("FROZEN_SOURCE_SHA_MISMATCH %s != %s",got,want)}
 return nil
}
func scan(path,want string)(Video,error){
 out:=Video{SHA256:want,MinimumTeal:1<<30,MinimumPink:1<<30}
 if e:=assertSHA(path,want);e!=nil{return out,e}
 ctx,cancel:=context.WithTimeout(context.Background(),75*time.Second);defer cancel()
 cmd:=exec.CommandContext(ctx,"ffmpeg","-hide_banner","-loglevel","error","-i",path,"-f","rawvideo","-pix_fmt","rgb24","-vsync","0","-")
 var log bytes.Buffer;cmd.Stderr=&log
 pipe,e:=cmd.StdoutPipe();if e!=nil{return out,e}
 if e=cmd.Start();e!=nil{return out,e}
 b:=make([]byte,width*height*3)
 for i:=0;i<frames;i++{
  if _,e=io.ReadFull(pipe,b);e!=nil{_ = cmd.Process.Kill();_ = cmd.Wait();return out,fmt.Errorf("NATIVE_FRAME_MISSING_%d: %w",i,e)}
  counts:=countPixels(b);out.Counts=append(out.Counts,counts)
  if counts.Teal<out.MinimumTeal{out.MinimumTeal=counts.Teal}
  if counts.Pink<out.MinimumPink{out.MinimumPink=counts.Pink}
  if counts.Teal>=minPixels && counts.Pink>=minPixels{out.BothAbove500++}
 }
 extra:=make([]byte,1)
 n,e:=pipe.Read(extra)
 if n!=0 || (e!=io.EOF && e!=nil){_ = cmd.Process.Kill();_ = cmd.Wait();return out,errors.New("SURPLUS_NATIVE_FRAME_OR_IO")}
 if e=cmd.Wait();e!=nil{return out,fmt.Errorf("FFMPEG_NATIVE_DECODE: %w %s",e,log.String())}
 out.Frames=len(out.Counts)
 return out,nil
}
func qualify(before,after map[string]Video) error {
 for _,v:=range []string{"front","oblique"}{
  b,a:=before[v],after[v]
  if b.Frames!=frames || a.Frames!=frames{return fmt.Errorf("NATIVE_FRAME_COUNT_%s",v)}
  if a.BothAbove500!=frames{return fmt.Errorf("AFTER_ACTOR_COLOR_OCCLUDED_%s",v)}
 }
 if before["oblique"].BothAbove500>=frames{return errors.New("ORIGINAL_RED_NOT_REPRODUCED")}
 return nil
}
func main(){
 bf:=flag.String("before-front","","original front H264");bo:=flag.String("before-oblique","","original oblique H264")
 af:=flag.String("after-front","","corrected front H264");ao:=flag.String("after-oblique","","corrected oblique H264")
 target:=flag.String("out","","independent JSON receipt");flag.Parse()
 paths:=map[string]string{"before_front":*bf,"before_oblique":*bo,"after_front":*af,"after_oblique":*ao}
 for k,v:=range paths{if v==""{fmt.Fprintln(os.Stderr,"SOURCE_REQUIRED",k);os.Exit(2)}}
 if *target==""{fmt.Fprintln(os.Stderr,"OUTPUT_REQUIRED");os.Exit(2)}
 rec:=Receipt{Schema:"scp.original_two_camera_color_visibility.v1",Status:"OBSERVATIONAL_VISIBILITY_ONLY",Before:map[string]Video{},After:map[string]Video{},VisibilityOnly:true,HumanGait:"UNKNOWN",PhysicalContact:"UNKNOWN",ProductAccepted:false}
 for _,k:=range []string{"before_front","before_oblique","after_front","after_oblique"}{
  v,e:=scan(paths[k],pinned[k]);if e!=nil{fmt.Fprintln(os.Stderr,k,e);os.Exit(3)}
  if k[:6]=="before"{rec.Before[k[7:]]=v}else{rec.After[k[6:]]=v}
 }
 if e:=qualify(rec.Before,rec.After);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(4)}
 output,e:=json.MarshalIndent(rec,"","  ");if e!=nil{panic(e)}
 output=append(output,'
');if e=os.WriteFile(*target,output,0600);e!=nil{panic(e)}
 fmt.Printf("%s: ORIGINAL_OBLIQUE=%d/72 CORRECTED_FRONT=%d/72 CORRECTED_OBLIQUE=%d/72; product=false
",rec.Status,rec.Before["oblique"].BothAbove500,rec.After["front"].BothAbove500,rec.After["oblique"].BothAbove500)
}
