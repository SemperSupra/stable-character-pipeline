// Native output quality gate: complete decode, channel count, duration, SHA256
// and finite nonzero samples. No spatial perceptual claim.
package main
import(
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "math"
 "os"
 "os/exec"
 "strconv"
)
type Probe struct{
 Streams []struct{Codec string `json:"codec_name"`;Rate string `json:"sample_rate"`;Channels int `json:"channels"`} `json:"streams"`
 Format struct{Duration string `json:"duration"`} `json:"format"`
}
func check(path,profile string)(string,error){
 channels:=0;switch profile{case "surround_5_1":channels=6;case "binaural","stereo_derived":channels=2;default:return "",errors.New("unqualified profile")}
 stat,e:=os.Lstat(path);if e!=nil{return "",e}
 if !stat.Mode().IsRegular() || stat.Mode()&os.ModeSymlink!=0{return "",errors.New("nonregular output")}
 b,e:=exec.Command("ffprobe","-v","error","-select_streams","a:0","-show_entries","stream=codec_name,sample_rate,channels","-show_entries","format=duration","-of","json",path).Output()
 if e!=nil{return "",e}
 var p Probe;if e=json.Unmarshal(b,&p);e!=nil{return "",e}
 if len(p.Streams)!=1 || p.Streams[0].Channels!=channels || p.Streams[0].Rate!="48000" || p.Streams[0].Codec!="pcm_f32le"{return "",errors.New("output channel/rate/codec mismatch")}
 duration,e:=strconv.ParseFloat(p.Format.Duration,64);if e!=nil || math.Abs(duration-1)>1e-6{return "",errors.New("one-second scene duration drift")}
 raw,e:=exec.Command("ffmpeg","-hide_banner","-nostdin","-v","error","-xerror","-i",path,"-f","f32le","-acodec","pcm_f32le","-").Output()
 if e!=nil{return "",e}
 if len(raw)!=48000*channels*4{return "",errors.New("source/target sample count mismatch")}
 powers:=make([]float64,channels);peak:=0.0
 for i:=0;i<len(raw)/4;i++{
  v:=float64(math.Float32frombits(binary.LittleEndian.Uint32(raw[i*4:i*4+4])))
  if math.IsNaN(v)||math.IsInf(v,0){return "",errors.New("NaN/Inf in native output")}
  powers[i%channels]+=v*v;peak=math.Max(peak,math.Abs(v))
 }
 if peak<1e-7||peak>1.0{return "",errors.New("silent or clipped native output")}
 audible:=0;for _,p:=range powers{if p>1e-8{audible++}}
 if audible<2{return "",errors.New("too few audible channels")}
 file,e:=os.ReadFile(path);if e!=nil{return "",e};h:=sha256.Sum256(file)
 return fmt.Sprintf("native_scene_audio_PASS profile=%s channels=%d frames=48000 peak=%.6f audible=%d sha256=%s",profile,channels,peak,audible,hex.EncodeToString(h[:])),nil
}
func main(){
 if len(os.Args)!=3{fmt.Fprintln(os.Stderr,"usage: nativeverify PROFILE OUTPUT.wav");os.Exit(2)}
 receipt,e:=check(os.Args[2],os.Args[1]);if e!=nil{fmt.Fprintln(os.Stderr,"NATIVE_SCENE_AUDIO_FAIL",e);os.Exit(1)}
 fmt.Println(receipt)
}
