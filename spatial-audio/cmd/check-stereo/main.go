// Command check-stereo qualifies explicit 5.1 -> stereo delivery, not the native stereo renderer.
// Exact input 5.1 speaker order is asserted by the separately compiled native C++ layout oracle.
package main

import (
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

const rate=48000
const samples=24576

type StreamProbe struct{
 Streams []struct{ Codec string `json:"codec_name"`; Rate string `json:"sample_rate"`; Channels int `json:"channels"` } `json:"streams"`
 Format struct{Duration string `json:"duration"`} `json:"format"`
}
func qualify(path string)(string,error){
 info,e:=os.Lstat(path);if e!=nil{return "",e}
 if !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink!=0 || info.Size()<=44{return "",errors.New("stereo must be a nontrivial regular file")}
 probe,e:=exec.Command("ffprobe","-v","error","-show_entries","stream=codec_name,sample_rate,channels","-show_entries","format=duration","-select_streams","a:0","-of","json",path).Output();if e!=nil{return "",e}
 var p StreamProbe;if e=json.Unmarshal(probe,&p);e!=nil{return "",e}
 if len(p.Streams)!=1||p.Streams[0].Codec!="pcm_f32le"||p.Streams[0].Rate!=strconv.Itoa(rate)||p.Streams[0].Channels!=2{return "",errors.New("wrong stereo WAV format")}
 duration,e:=strconv.ParseFloat(p.Format.Duration,64);if e!=nil||math.Abs(duration-float64(samples)/rate)>0.000001{return "",errors.New("duration mismatch")}
 raw,e:=exec.Command("ffmpeg","-nostdin","-hide_banner","-v","error","-xerror","-i",path,"-f","f32le","-acodec","pcm_f32le","-").Output();if e!=nil{return "",e}
 if len(raw)!=samples*2*4{return "",errors.New("wrong decoded sample count")}
 energy:=[2]float64{};sumDiff:=0.0;peak:=0.0
 for i:=0;i<len(raw);i+=8{
  left:=float64(math.Float32frombits(binary.LittleEndian.Uint32(raw[i:i+4])))
  right:=float64(math.Float32frombits(binary.LittleEndian.Uint32(raw[i+4:i+8])))
  if math.IsNaN(left)||math.IsInf(left,0)||math.IsNaN(right)||math.IsInf(right,0){return "",errors.New("nonfinite output")}
  peak=math.Max(peak,math.Max(math.Abs(left),math.Abs(right)))
  energy[0]+=left*left;energy[1]+=right*right
  sumDiff+=math.Abs(left-right)
 }
 if peak<1e-7||peak>1||energy[0]<1e-7||energy[1]<1e-7||sumDiff<1e-7{return "",errors.New("silent/clipped/duplicated stereo output")}
 wav,e:=os.ReadFile(path);if e!=nil{return "",e}
 sum:=sha256.Sum256(wav)
 return fmt.Sprintf("spatial_stereo_downmix_PASS channels=2 duration_s=%.3f peak=%.6f left_energy=%.6f right_energy=%.6f sha256=%s native_stereo_UNQUALIFIED=true discrete_LFE_dropped=true",duration,peak,energy[0],energy[1],hex.EncodeToString(sum[:])),nil
}
func main(){
 if len(os.Args)!=2{fmt.Fprintln(os.Stderr,"usage: check-stereo OUTPUT_STEREO_WAV");os.Exit(2)}
 receipt,e:=qualify(os.Args[1]);if e!=nil{fmt.Fprintln(os.Stderr,"STEREO_DOWNMIX_FIRST_FAILURE",e);os.Exit(1)}
 fmt.Println(receipt)
}
