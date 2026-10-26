// Public synthetic robot/computer voice effects. No private/final voice assets in CI.
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
 "os"
 "os/exec"
 "path/filepath"
 "regexp"
 "strconv"
 "strings"
 "time"
)

const classification = "PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL"

type preset struct {
 Name string
 Filter string
}

var profiles = []preset{
 {"computer","highpass=f=140,lowpass=f=6600,acompressor=threshold=0.11:ratio=2.3:attack=10:release=120,volume=0.90"},
 {"classic-robot","highpass=f=260,lowpass=f=3100,acrusher=bits=8:mode=lin:mix=0.55,tremolo=f=12:d=0.45,volume=0.85"},
 {"social-robot","highpass=f=90,lowpass=f=9000,acompressor=threshold=0.12:ratio=1.7:attack=12:release=110,aecho=0.8:0.35:55:0.10,volume=0.87"},
}
var presentations = []string{"feminine","masculine","unspecified"}
var meanPattern=regexp.MustCompile("mean_volume:\\s*(-?[0-9.]+) dB")
var peakPattern=regexp.MustCompile("max_volume:\\s*(-?[0-9.]+) dB")

type clip struct {
 Presentation string `json:"presentation"`
 Style string `json:"style"`
 InputSHA256 string `json:"input_sha256"`
 OutputSHA256 string `json:"output_sha256"`
 AACSHA256 string `json:"aac_sha256"`
 PCMBytes int64 `json:"pcm_bytes"`
 AACBytes int64 `json:"aac_bytes"`
 DurationSeconds float64 `json:"duration_seconds"`
 MeanDBFS float64 `json:"mean_dbfs"`
 PeakDBFS float64 `json:"peak_dbfs"`
}
type receipt struct {
 Schema string `json:"schema"`
 Classification string `json:"classification"`
 Description string `json:"description"`
 SampleRateHz int `json:"sample_rate_hz"`
 Channels int `json:"channels"`
 VoiceSourceProvider string `json:"voice_source_provider"`
 Clips []clip `json:"clips"`
}
type probe struct {
 Streams []struct{
  Codec string `json:"codec_name"`
  Rate string `json:"sample_rate"`
  Channels int `json:"channels"`
 } `json:"streams"`
 Format struct{ Duration string `json:"duration"` } `json:"format"`
}
func hash(path string)(string,int64,error){
 f,e:=os.Open(path);if e!=nil{return "",0,e}
 defer f.Close()
 h:=sha256.New()
 n,e:=io.Copy(h,f)
 return hex.EncodeToString(h.Sum(nil)),n,e
}
func validateLocation(root,file string)error{
 if info,e:=os.Lstat(root);e!=nil || !info.IsDir() || info.Mode()&os.ModeSymlink!=0{return errors.New("source root must be a real directory")}
 p:=filepath.Join(root,file)
 st,e:=os.Lstat(p)
 if e!=nil || !st.Mode().IsRegular() || st.Mode()&os.ModeSymlink!=0{return errors.New("missing or nonregular source "+file)}
 return nil
}
func validateArgs(source,output,class string)error{
 if source=="" || output==""{return errors.New("--sources and --out are required")}
 if class!=classification{return errors.New("public synthetic class required; private final character voices are never admitted to public CI")}
 if _,e:=os.Lstat(output);e==nil{return errors.New("output exists: refusing overwrite")}else if !os.IsNotExist(e){return e}
 if st,e:=os.Stat(filepath.Dir(output));e!=nil || !st.IsDir(){return errors.New("output parent must exist")}
 for _,v:=range presentations{if e:=validateLocation(source,v+".wav");e!=nil{return e}}
 return nil
}
func execute(ctx context.Context,name string,args ...string)([]byte,error){
 b,e:=exec.CommandContext(ctx,name,args...).CombinedOutput()
 if e!=nil{return b,fmt.Errorf("%s exited: %w (%s)",name,e,string(b))}
 return b,nil
}
func probeAudio(ctx context.Context,path,codec string,rate,channels int)(float64,error){
 b,e:=execute(ctx,"ffprobe","-v","error","-show_entries","stream=codec_name,sample_rate,channels","-show_entries","format=duration","-of","json",path)
 if e!=nil{return 0,e}
 var p probe
 if e=json.Unmarshal(b,&p);e!=nil{return 0,e}
 if len(p.Streams)!=1 || p.Streams[0].Codec!=codec || p.Streams[0].Rate!=strconv.Itoa(rate) || p.Streams[0].Channels!=channels{return 0,fmt.Errorf("codec/rate/channels mismatch: %s",filepath.Base(path))}
 d,e:=strconv.ParseFloat(p.Format.Duration,64)
 if e!=nil|| d<0.5 || d>30{return 0,errors.New("invalid clip duration")}
 return d,nil
}
func levels(ctx context.Context,path string)(float64,float64,error){
 b,e:=execute(ctx,"ffmpeg","-hide_banner","-nostdin","-i",path,"-af","volumedetect","-f","null","-")
 if e!=nil{return 0,0,e}
 a,z:=meanPattern.FindStringSubmatch(string(b)),peakPattern.FindStringSubmatch(string(b))
 if len(a)<2||len(z)<2{return 0,0,errors.New("missing level metrics")}
 mean,_:=strconv.ParseFloat(a[1],64)
 peak,_:=strconv.ParseFloat(z[1],64)
 if mean < -53.0 || peak > -0.2 || peak < -45.0 {return mean,peak,fmt.Errorf("unusable audio level mean=%v peak=%v",mean,peak)}
 return mean,peak,nil
}
func render(sources,out,provider string) (receipt,error){
 r:=receipt{Schema:"audio_foundry.robot_voice.v1",Classification:classification,Description:"Independent voice presentation and robot DSP; synthetic candidate, NOT final character voice; no claim of perceived neutrality",SampleRateHz:48000,Channels:2,VoiceSourceProvider:provider}
 if provider=="" || strings.ContainsAny(provider,"/\\\\\n\r") || len(provider)>72{return r,errors.New("invalid provider descriptor")}
 if e:=validateArgs(sources,out,classification);e!=nil{return r,e}
 ctx,cancel:=context.WithTimeout(context.Background(),110*time.Second);defer cancel()
 if e:=os.Mkdir(out,0700);e!=nil{return r,e}
 // Distinct output paths cannot overwrite. Failure leaves a visible partial
 // output directory for inspection; CI cleans ephemeral media on exit.
 for _,v:=range presentations {
  source:=filepath.Join(sources,v+".wav")
  inHash,_,e:=hash(source);if e!=nil{return r,e}
  duration,e:=probeAudio(ctx,source,"pcm_s16le",24000,1);if e!=nil{return r,fmt.Errorf("source %s: %w",v,e)}
  for _,p:=range profiles{
   basename:=v+"_"+p.Name
   wav:=filepath.Join(out,basename+".wav")
   // FFmpeg is the existing audio backend. Source is strictly located and
   // preset filters are immutable compile-time constants, never user code.
   if _,e=execute(ctx,"ffmpeg","-hide_banner","-loglevel","error","-nostdin","-n","-i",source,"-af",p.Filter+",apad,atrim=duration="+strconv.FormatFloat(duration,'f',3,64),"-ar","48000","-ac","2","-c:a","pcm_s16le",wav);e!=nil{return r,e}
   actual,e:=probeAudio(ctx,wav,"pcm_s16le",48000,2);if e!=nil{return r,e}
   if actual<duration-0.04 || actual>duration+0.04{return r,errors.New("unexpected output length "+basename)}
   mean,peak,e:=levels(ctx,wav);if e!=nil{return r,fmt.Errorf("%s %w",basename,e)}
   wavHash,wavBytes,e:=hash(wav);if e!=nil{return r,e}
   aac:=filepath.Join(out,basename+".m4a")
   if _,e=execute(ctx,"ffmpeg","-hide_banner","-loglevel","error","-nostdin","-n","-i",wav,"-c:a","aac","-b:a","128k","-movflags","+faststart",aac);e!=nil{return r,e}
   if _,e=probeAudio(ctx,aac,"aac",48000,2);e!=nil{return r,e}
   aacHash,aacBytes,e:=hash(aac);if e!=nil{return r,e}
   r.Clips=append(r.Clips,clip{Presentation:v,Style:p.Name,InputSHA256:inHash,OutputSHA256:wavHash,AACSHA256:aacHash,PCMBytes:wavBytes,AACBytes:aacBytes,DurationSeconds:actual,MeanDBFS:mean,PeakDBFS:peak})
  }
 }
 b,e:=json.MarshalIndent(r,"","  ");if e!=nil{return r,e}
 if e=os.WriteFile(filepath.Join(out,"receipt.json"),append(b,'\n'),0600);e!=nil{return r,e}
 return r,nil
}
func main(){
 sources:=flag.String("sources","","directory containing synthetic feminine.wav, masculine.wav and unspecified.wav")
 output:=flag.String("out","","new output directory for 9 profiles and receipts")
 provider:=flag.String("provider","kokoro-onnx+espeak-ng","source generator; provenance descriptor")
 cls:=flag.String("classification",classification,"classification gate")
 flag.Parse()
 if e:=validateArgs(*sources,*output,*cls);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}
 rec,e:=render(*sources,*output,*provider)
 if e!=nil{fmt.Fprintln(os.Stderr,"ROBOT_VOICE_FIRST_FAILURE:",e);os.Exit(1)}
 fmt.Printf("robot_voice_PASS clips=%d classification=%s\\n",len(rec.Clips),rec.Classification)
}
