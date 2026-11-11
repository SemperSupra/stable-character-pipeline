package main

import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "math"
 "os"
 "os/exec"
 "path/filepath"
 "regexp"
 "strings"
 "time"
)
type Case struct {
 ID string `json:"id"`
 Kind string `json:"kind"`
 Path string `json:"path"`
 Expect string `json:"expect"`
 ExpectedMotion bool `json:"expected_motion,omitempty"`
}
type Manifest struct { Schema string `json:"schema"`; Cases []Case `json:"cases"` }
type Sample struct { Time float64 `json:"time_s"`; FootX float64 `json:"foot_x_m"`; FootY float64 `json:"foot_y_m"`; Contact *bool `json:"contact"` }
type Motion struct { Schema string `json:"schema"`; Samples []Sample `json:"samples"` }
type Result struct {
 ID string `json:"id"`
 Kind string `json:"kind"`
 SourceSHA256 string `json:"source_sha256"`
 Verdict string `json:"verdict"`
 Expected string `json:"expected"`
 MatchesOracle bool `json:"matches_oracle"`
 Findings []string `json:"findings"`
 Metrics map[string]float64 `json:"metrics"`
 Error string `json:"error,omitempty"`
}
type Receipt struct {
 Schema string `json:"schema"`
 Results []Result `json:"results"`
 Total int `json:"total"`
 Matched int `json:"matched"`
 Discrepancies int `json:"discrepancies"`
 ExecutedAt string `json:"executed_at_utc"`
 Limitations []string `json:"limitations"`
}
var freezeRx=regexp.MustCompile(`freeze_start:\s*([0-9.]+)`)
var blackRx=regexp.MustCompile(`black_start:\s*([0-9.]+)`)
func hashFile(path string)(string,error){
 f,e:=os.Open(path); if e!=nil{return "",e}
 defer f.Close()
 h:=sha256.New();if _,e=io.Copy(h,f);e!=nil{return "",e}
 return hex.EncodeToString(h.Sum(nil)),nil
}
func finite(f float64)bool{return !math.IsNaN(f)&&!math.IsInf(f,0)}
func analyzeMotion(path string)(string,[]string,map[string]float64,error){
 b,e:=os.ReadFile(path);if e!=nil{return "UNKNOWN",nil,nil,e}
 var m Motion
 if e=json.Unmarshal(b,&m);e!=nil{return "UNKNOWN",nil,nil,e}
 if m.Schema!="scp.motion-observation.v1"||len(m.Samples)<2{return "UNKNOWN",[]string{"INSUFFICIENT_MOTION_OBSERVATIONS"},nil,nil}
 total,n,peak:=0.0,0,0.0
 for i:=1;i<len(m.Samples);i++{
  p,q:=m.Samples[i-1],m.Samples[i]
  if !finite(p.Time)||!finite(q.Time)||!finite(p.FootX)||!finite(q.FootX)||!finite(p.FootY)||!finite(q.FootY)||q.Time<=p.Time {
   return "UNKNOWN",[]string{"UNTRUSTWORTHY_TIME_OR_POSITION"},nil,nil
  }
  if p.Contact==nil||q.Contact==nil{return "UNKNOWN",[]string{"CONTACT_NOT_OBSERVED"},nil,nil}
  if !*p.Contact||!*q.Contact{continue}
  v:=math.Hypot(q.FootX-p.FootX,q.FootY-p.FootY)/(q.Time-p.Time)
  total+=v;n++;if v>peak{peak=v}
 }
 if n==0{return "UNKNOWN",[]string{"NO_CONFIRMED_STANCE_INTERVAL"},nil,nil}
 metrics:=map[string]float64{"stance_mean_foot_speed_m_s":total/float64(n),"stance_peak_foot_speed_m_s":peak,"stance_intervals":float64(n)}
 if peak>0.03{return "FAIL",[]string{"PLANTED_FOOT_SLIDING"},metrics,nil}
 return "PASS",[]string{},metrics,nil
}
func analyzeVideo(path string,motion bool)(string,[]string,map[string]float64,error){
 ctx,cancel:=context.WithTimeout(context.Background(),35*time.Second);defer cancel()
 probe:=exec.CommandContext(ctx,"ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","json",path)
 b,e:=probe.CombinedOutput();if e!=nil{return "UNKNOWN",nil,nil,fmt.Errorf("ffprobe: %w: %s",e,b)}
 var p struct{Streams []struct{Width int `json:"width"`;Height int `json:"height"`} `json:"streams"`}
 if e=json.Unmarshal(b,&p);e!=nil{return "UNKNOWN",nil,nil,e}
 if len(p.Streams)!=1||p.Streams[0].Width<1||p.Streams[0].Height<1{return "UNKNOWN",[]string{"INVALID_VIDEO_STREAM"},nil,nil}
 cmd:=exec.CommandContext(ctx,"ffmpeg","-nostdin","-hide_banner","-i",path,"-vf","freezedetect=n=-50dB:d=0.35,blackdetect=d=0.25:pix_th=0.10","-an","-f","null","-")
 log,e:=cmd.CombinedOutput();if e!=nil{return "UNKNOWN",nil,nil,fmt.Errorf("ffmpeg: %w: %s",e,log)}
 freezes,black:=len(freezeRx.FindAll(log,-1)),len(blackRx.FindAll(log,-1))
 metric:=map[string]float64{"freeze_events":float64(freezes),"black_events":float64(black),"width":float64(p.Streams[0].Width),"height":float64(p.Streams[0].Height)}
 findings:=[]string{}
 if black>0{findings=append(findings,"BLACK_SEGMENT")}
 if freezes>0&&motion{findings=append(findings,"FROZEN_MOTION_EXPECTED")}
 if len(findings)>0{return "FAIL",findings,metric,nil}
 if freezes>0&&!motion{return "UNKNOWN",[]string{"STATIC_SCENE_OR_FREEZE_AMBIGUOUS"},metric,nil}
 return "PASS",findings,metric,nil
}
func evaluate(root string,c Case)Result{
 r:=Result{ID:c.ID,Kind:c.Kind,Expected:c.Expect,Verdict:"UNKNOWN",Findings:[]string{},Metrics:map[string]float64{}}
 if c.ID==""||c.Path==""||strings.Contains(c.Path,"..")||filepath.IsAbs(c.Path){r.Error="invalid id or path";return r}
 base,e:=filepath.EvalSymlinks(root);if e!=nil{r.Error="fixture root: "+e.Error();return r}
 path,e:=filepath.EvalSymlinks(filepath.Join(root,c.Path));if e!=nil{r.Error="fixture: "+e.Error();return r}
 rel,e:=filepath.Rel(base,path);if e!=nil||rel==".."||strings.HasPrefix(rel,".."+string(os.PathSeparator)){r.Error="fixture escapes root";return r}
 sha,e:=hashFile(path);if e!=nil{r.Error=e.Error();return r};r.SourceSHA256=sha
 switch c.Kind{
 case "motion":r.Verdict,r.Findings,r.Metrics,e=analyzeMotion(path)
 case "video":r.Verdict,r.Findings,r.Metrics,e=analyzeVideo(path,c.ExpectedMotion)
 default:e=errors.New("unsupported case kind")
 }
 if e!=nil{r.Error=e.Error();r.Verdict="UNKNOWN"}
 r.MatchesOracle=r.Error==""&&r.Verdict==r.Expected
 return r
}
func run(manifest,output string)error{
 b,e:=os.ReadFile(manifest);if e!=nil{return e}
 var m Manifest;if e=json.Unmarshal(b,&m);e!=nil{return e}
 if m.Schema!="scp.video-bakeoff-cases.v1"||len(m.Cases)==0{return errors.New("invalid manifest")}
 receipt:=Receipt{Schema:"scp.video-bakeoff-receipt.v1",Results:[]Result{},Total:len(m.Cases),ExecutedAt:time.Now().UTC().Format(time.RFC3339),Limitations:[]string{"Synthetic cases only; real-human biomechanics remain UNKNOWN","FFmpeg freeze may be intentional; expected_motion controls interpretation","Kinematic witnesses require trusted contact and calibrated coordinates","Upstream-source acquisition does not qualify installation/inference/weights"}}
 seen:=map[string]bool{}
 for _,c:=range m.Cases{
  if seen[c.ID]{return fmt.Errorf("duplicate id %q",c.ID)};seen[c.ID]=true
  if c.Expect!="PASS"&&c.Expect!="FAIL"&&c.Expect!="UNKNOWN"{return fmt.Errorf("invalid oracle for %s",c.ID)}
  r:=evaluate(filepath.Dir(manifest),c);receipt.Results=append(receipt.Results,r)
  if r.MatchesOracle{receipt.Matched++}else{receipt.Discrepancies++}
 }
 data,_:=json.MarshalIndent(receipt,"","  ");data=append(data,'\n')
 if output==""{fmt.Print(string(data))}else{if e=os.WriteFile(output,data,0600);e!=nil{return e}}
 if receipt.Discrepancies>0{return fmt.Errorf("%d/%d oracle mismatches",receipt.Discrepancies,receipt.Total)}
 return nil
}
func main(){
 manifest:=flag.String("manifest","fixtures/cases.json","case manifest")
 out:=flag.String("out","","receipt")
 flag.Parse()
 if e:=run(*manifest,*out);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}
}
