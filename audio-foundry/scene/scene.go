// Package scene is the versioned public Audio Foundry soundtrack contract.
package scene
import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "math"
 "os"
 "os/exec"
 "path/filepath"
 "regexp"
 "strconv"
 "strings"
 "time"
)
const Schema="scene_audio.v1"
const Public="PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL"
const Private="PRIVATE_FINAL_CHARACTER_VOICE"
var ident=regexp.MustCompile("^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
var allowed=map[string]bool{"human_voice":true,"robot_voice":true,"fauna":true,"alien_voice":true,"music":true,"ambience":true,"foley":true,"mechanical":true,"effects":true}
type Track struct {
 ID string `json:"id"`
 Category string `json:"category"`
 Asset string `json:"asset"`
 SHA256 string `json:"sha256"`
 StartMS int `json:"start_ms"`
 OffsetMS int `json:"offset_ms"`
 DurationMS int `json:"duration_ms"`
 GainDB float64 `json:"gain_db"`
 FadeInMS int `json:"fade_in_ms"`
 FadeOutMS int `json:"fade_out_ms"`
}
type Event struct {
 ID string `json:"id"`
 TrackID string `json:"track_id"`
 EntityID string `json:"entity_id"`
 Kind string `json:"kind"`
 TimeMS int `json:"time_ms"`
 PositionM [3]float64 `json:"position_m"`
}
type Manifest struct {
 Schema string `json:"schema"`
 ID string `json:"id"`
 Classification string `json:"classification"`
 DurationMS int `json:"duration_ms"`
 SampleRateHz int `json:"sample_rate_hz"`
 Channels int `json:"channels"`
 Tracks []Track `json:"tracks"`
 Events []Event `json:"events"`
}
type Asset struct {
 TrackID string `json:"track_id"`
 SHA256 string `json:"sha256"`
 Bytes int64 `json:"bytes"`
}
type Receipt struct {
 Schema string `json:"schema"`
 SceneID string `json:"scene_id"`
 Classification string `json:"classification"`
 ManifestSHA256 string `json:"manifest_sha256"`
 Assets []Asset `json:"assets"`
 OutputSHA256 string `json:"output_sha256,omitempty"`
 OutputBytes int64 `json:"output_bytes,omitempty"`
 MeanDBFS float64 `json:"mean_dbfs"`
 PeakDBFS float64 `json:"peak_dbfs"`
}
func Load(path string)(Manifest,error) {
 f,e:=os.Open(path);if e!=nil{return Manifest{},e};defer f.Close()
 d:=json.NewDecoder(io.LimitReader(f,1<<20));d.DisallowUnknownFields()
 var m Manifest
 if e=d.Decode(&m);e!=nil{return m,e}
 var extra interface{}
 if e=d.Decode(&extra);e!=io.EOF{return m,errors.New("trailing JSON")}
 return m,m.Validate()
}
func SafeAsset(p string)bool {
 if p=="" || !filepath.IsLocal(p) || filepath.Clean(p)!=p || strings.Contains(p,"\\") || strings.HasPrefix(p,".") || !strings.EqualFold(filepath.Ext(p),".wav"){return false}
 return true
}
func (m Manifest)Validate()error {
 if m.Schema!=Schema || !ident.MatchString(m.ID){return errors.New("invalid scene schema/id")}
 if m.Classification!=Public && m.Classification!=Private{return errors.New("unknown custody classification")}
 if m.DurationMS<1 || m.DurationMS>600000 || (m.SampleRateHz!=48000 && m.SampleRateHz!=44100) || (m.Channels!=1 && m.Channels!=2){return errors.New("unsupported duration/rate/channels")}
 if len(m.Tracks)<1 || len(m.Tracks)>32{return errors.New("invalid track count")}
 ids:=map[string]bool{}
 for _,t:=range m.Tracks {
  if !ident.MatchString(t.ID) || ids[t.ID] || !allowed[t.Category] || !SafeAsset(t.Asset){return fmt.Errorf("invalid/duplicate track %q",t.ID)}
  ids[t.ID]=true
  if len(t.SHA256)!=64 || strings.ToLower(t.SHA256)!=t.SHA256{return fmt.Errorf("invalid source digest for %s",t.ID)}
  if _,e:=hex.DecodeString(t.SHA256);e!=nil{return fmt.Errorf("invalid source digest for %s: %w",t.ID,e)}
  if t.StartMS<0 || t.OffsetMS<0 || t.DurationMS<1 || t.StartMS>m.DurationMS || t.DurationMS>m.DurationMS-t.StartMS || t.FadeInMS<0 || t.FadeOutMS<0 || t.FadeInMS+t.FadeOutMS>t.DurationMS{return fmt.Errorf("track timing failed %s",t.ID)}
  if math.IsNaN(t.GainDB)||math.IsInf(t.GainDB,0)||t.GainDB< -60 || t.GainDB>12{return fmt.Errorf("gain failed %s",t.ID)}
 }
 evs:=map[string]bool{}
 if len(m.Events)>1024{return errors.New("too many events")}
 for _,v:=range m.Events {
  if !ident.MatchString(v.ID)||evs[v.ID]||!ids[v.TrackID]||!ident.MatchString(v.EntityID)||!ident.MatchString(v.Kind)||v.TimeMS<0||v.TimeMS>=m.DurationMS{return fmt.Errorf("bad event %s",v.ID)}
  evs[v.ID]=true
  for _,n:=range v.PositionM {if math.IsNaN(n)||math.IsInf(n,0)||math.Abs(n)>100000{return errors.New("invalid world position")}}
 }
 return nil
}
func Hash(path string)(string,int64,error){
 f,e:=os.Open(path);if e!=nil{return "",0,e};defer f.Close()
 h:=sha256.New();n,e:=io.Copy(h,f);if e!=nil{return "",0,e}
 return hex.EncodeToString(h.Sum(nil)),n,nil
}
func (m Manifest)Plan(root string,privateOK bool)(Receipt,error){
 if e:=m.Validate();e!=nil{return Receipt{},e}
 if m.Classification==Private && !privateOK{return Receipt{},errors.New("private-final content is blocked on public workers")}
 realRoot,e:=filepath.EvalSymlinks(root);if e!=nil{return Receipt{},e}
 if st,e:=os.Stat(realRoot);e!=nil || !st.IsDir(){return Receipt{},errors.New("missing asset directory")}
 b,_:=json.Marshal(m);h:=sha256.Sum256(b)
 r:=Receipt{Schema:"scene_audio.receipt.v1",SceneID:m.ID,Classification:m.Classification,ManifestSHA256:hex.EncodeToString(h[:])}
 for _,t:=range m.Tracks{
  path:=filepath.Join(realRoot,t.Asset)
  resolved,e:=filepath.EvalSymlinks(path);if e!=nil{return Receipt{},e}
  rel,e:=filepath.Rel(realRoot,resolved);if e!=nil || !filepath.IsLocal(rel) || resolved!=path{return Receipt{},errors.New("asset escapes root or is symlink: "+t.Asset)}
  st,e:=os.Stat(path);if e!=nil || !st.Mode().IsRegular(){return Receipt{},errors.New("asset not regular file: "+t.Asset)}
  digest,n,e:=Hash(path);if e!=nil{return Receipt{},e}
  if digest!=t.SHA256{return Receipt{},errors.New("source digest mismatch: "+t.Asset)}
  r.Assets=append(r.Assets,Asset{TrackID:t.ID,SHA256:digest,Bytes:n})
 }
 return r,nil
}
func secs(ms int)string{return strconv.FormatFloat(float64(ms)/1000,'f',3,64)}
func Layout(ch int)string{if ch==1{return "mono"};return "stereo"}
func (m Manifest)Filter()string{
 var nodes,labels []string
 for i,t:=range m.Tracks{
  v:=fmt.Sprintf("[%d:a]atrim=start=%s:duration=%s,asetpts=PTS-STARTPTS,aresample=%d,aformat=channel_layouts=%s,volume=%.3fdB",i,secs(t.OffsetMS),secs(t.DurationMS),m.SampleRateHz,Layout(m.Channels),t.GainDB)
  if t.FadeInMS>0{v+=",afade=t=in:st=0:d="+secs(t.FadeInMS)}
  if t.FadeOutMS>0{v+=",afade=t=out:st="+secs(t.DurationMS-t.FadeOutMS)+":d="+secs(t.FadeOutMS)}
  if t.StartMS>0{v+=fmt.Sprintf(",adelay=%d:all=1",t.StartMS)}
  label:=fmt.Sprintf("[a%d]",i);nodes=append(nodes,v+label);labels=append(labels,label)
 }
 nodes=append(nodes,strings.Join(labels,"")+fmt.Sprintf("amix=inputs=%d:duration=longest:normalize=0,alimiter=limit=0.92,apad,atrim=duration=%s[aout]",len(labels),secs(m.DurationMS)))
 return strings.Join(nodes,";")
}
type probe struct{
 Streams []struct{Codec string `json:"codec_name"`; Rate string `json:"sample_rate"`; Channels int `json:"channels"`} `json:"streams"`
 Format struct{Duration string `json:"duration"`} `json:"format"`
}
func VerifyWave(ctx context.Context,path string,rate,channels int,minSeconds,expectedSeconds float64)error{
 b,e:=exec.CommandContext(ctx,"ffprobe","-v","error","-select_streams","a:0","-show_entries","stream=codec_name,sample_rate,channels","-show_entries","format=duration","-of","json",path).Output()
 if e!=nil{return fmt.Errorf("ffprobe: %w",e)}
 var p probe;if e=json.Unmarshal(b,&p);e!=nil{return e}
 if len(p.Streams)!=1 || p.Streams[0].Codec!="pcm_s16le" || p.Streams[0].Rate!=strconv.Itoa(rate) || p.Streams[0].Channels!=channels{return errors.New("input/output wave must be PCM 16-bit at scene sample rate and channels")}
 d,e:=strconv.ParseFloat(p.Format.Duration,64);if e!=nil || d+0.02<minSeconds || (expectedSeconds>0 && math.Abs(d-expectedSeconds)>0.02){return errors.New("short or incorrect audio duration")}
 return nil
}
var meanRE=regexp.MustCompile("mean_volume:\\s*(-?[0-9.]+) dB")
var peakRE=regexp.MustCompile("max_volume:\\s*(-?[0-9.]+) dB")
func MixQC(ctx context.Context,path string)(float64,float64,error){
 b,e:=exec.CommandContext(ctx,"ffmpeg","-hide_banner","-nostdin","-i",path,"-af","volumedetect","-f","null","-").CombinedOutput()
 if e!=nil{return 0,0,e}
 a,z:=meanRE.FindStringSubmatch(string(b)),peakRE.FindStringSubmatch(string(b))
 if len(a)!=2 || len(z)!=2{return 0,0,errors.New("missing volume metrics or silent output")}
 mean,_:=strconv.ParseFloat(a[1],64);peak,_:=strconv.ParseFloat(z[1],64)
 if mean< -60 || peak> -0.2{return mean,peak,fmt.Errorf("audio level rejected: mean %.1f dBFS, peak %.1f dBFS",mean,peak)}
 return mean,peak,nil
}
func (m Manifest)Render(root,out string,privateOK bool)(Receipt,error){
 r,e:=m.Plan(root,privateOK);if e!=nil{return r,e}
 if filepath.Ext(out)!=".wav"{return r,errors.New("output must be WAV")}
 if _,e=os.Lstat(out);e==nil{return r,errors.New("refusing overwrite")}else if !os.IsNotExist(e){return r,e}
 dir:=filepath.Dir(out)
 if st,e:=os.Stat(dir);e!=nil || !st.IsDir(){return r,errors.New("missing output directory")}
 ctx,cancel:=context.WithTimeout(context.Background(),90*time.Second);defer cancel()
 for _,t:=range m.Tracks{
  if e=VerifyWave(ctx,filepath.Join(root,t.Asset),m.SampleRateHz,m.Channels,float64(t.OffsetMS+t.DurationMS)/1000,0);e!=nil{return r,e}
 }
 temp,e:=os.CreateTemp(dir,".soundtrack-*.wav");if e!=nil{return r,e}
 p:=temp.Name();_ =temp.Close();defer os.Remove(p)
 args:=[]string{"-hide_banner","-loglevel","error","-nostdin","-y"}
 for _,t:=range m.Tracks{args=append(args,"-i",filepath.Join(root,t.Asset))}
 args=append(args,"-filter_complex",m.Filter(),"-map","[aout]","-ar",strconv.Itoa(m.SampleRateHz),"-ac",strconv.Itoa(m.Channels),"-c:a","pcm_s16le","-f","wav",p)
 if output,e:=exec.CommandContext(ctx,"ffmpeg",args...).CombinedOutput();e!=nil{return r,fmt.Errorf("mix: %w (%s)",e,string(output))}
 if _,e=m.Plan(root,privateOK);e!=nil{return r,e}
 if e=VerifyWave(ctx,p,m.SampleRateHz,m.Channels,0,float64(m.DurationMS)/1000);e!=nil{return r,e}
 mean,peak,e:=MixQC(ctx,p);if e!=nil{return r,e}
 h,n,e:=Hash(p);if e!=nil{return r,e}
 src,e:=os.Open(p);if e!=nil{return r,e};defer src.Close()
 dst,e:=os.OpenFile(out,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600);if e!=nil{return r,e}
 written,copyErr:=io.Copy(dst,src);closeErr:=dst.Close()
 if copyErr!=nil || closeErr!=nil || n!=written{_ =os.Remove(out);return r,errors.New("finalize output failed")}
 r.OutputBytes=n;r.OutputSHA256=h;r.MeanDBFS=mean;r.PeakDBFS=peak
 return r,nil
}
func Example(root string)(Manifest,error){
 specs:=[]struct{id,category,file string; start,duration int}{
  {"wind","ambience","ambience_wind.wav",0,12000},
  {"music","music","music_pad.wav",0,12000},
  {"birds","fauna","fauna_chirps.wav",1100,9000},
  {"contacts","foley","foley_texture.wav",600,11000},
  {"human","human_voice","human_voice.wav",0,12000},
  {"computer","robot_voice","robot_voice.wav",0,12000},
 }
 m:=Manifest{Schema:Schema,ID:"original_synthetic_scene",Classification:Public,DurationMS:12000,SampleRateHz:48000,Channels:2}
 for _,spec:=range specs{
  sha,_,e:=Hash(filepath.Join(root,spec.file));if e!=nil{return m,e}
  m.Tracks=append(m.Tracks,Track{ID:spec.id,Category:spec.category,Asset:spec.file,SHA256:sha,StartMS:spec.start,DurationMS:spec.duration})
 }
 m.Events=[]Event{{ID:"bird_call",TrackID:"birds",EntityID:"fictional_bird_1",Kind:"vocalization",TimeMS:1100,PositionM:[3]float64{8,3,4}},{ID:"robot_status",TrackID:"computer",EntityID:"fictional_robot_1",Kind:"status_speech",TimeMS:7600,PositionM:[3]float64{1,0,1}}}
 return m,m.Validate()
}
func JSON(v interface{})error{e:=json.NewEncoder(os.Stdout);e.SetIndent("","  ");return e.Encode(v)}
