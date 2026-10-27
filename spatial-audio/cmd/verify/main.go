// Command verify checks public synthetic spatial audio render artifacts independently
// of the C++ emitter; it never assumes a WAVE file declares speaker identities.
package main

import (
 "bufio"
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
 "strconv"
 "strings"
)

const frames=24576
const rate=48000

var expected=map[string]int{"stereo":2,"binaural":2,"surround_5_1":6,"surround_7_1":8,"immersive_5_1_4":10,"immersive_7_1_4":12}

type Receipt struct {
 Profile string `json:"profile"`
 Channels int `json:"channels"`
 SamplesPerChannel int `json:"samples_per_channel"`
 Peak float64 `json:"peak"`
 ChannelEnergy []float64 `json:"channel_energy"`
 WAV string `json:"wav"`
}
type Probe struct {
 Streams []struct{
  Codec string `json:"codec_name"`
  Rate string `json:"sample_rate"`
  Channels int `json:"channels"`
 } `json:"streams"`
 Format struct{Duration string `json:"duration"`} `json:"format"`
}
func checkReceipt(r Receipt)error{
 channels,ok:=expected[r.Profile]
 if !ok{return fmt.Errorf("unsupported profile %q",r.Profile)}
 if r.Channels!=channels || len(r.ChannelEnergy)!=channels || r.SamplesPerChannel!=frames{return errors.New("channels, energy or sample count mismatch")}
 if r.WAV!=r.Profile+".wav"{return errors.New("unexpected or escaping WAV file name")}
 if !isFinite(r.Peak) || r.Peak<=1e-7 || r.Peak>1.0{return errors.New("silent, invalid or clipping output")}
 nonzero:=false
 for _,e:=range r.ChannelEnergy{if !isFinite(e)||e<0{return errors.New("invalid channel energy")};nonzero=nonzero || e>0}
 if !nonzero{return errors.New("zero channel energy")}
 return nil
}
func isFinite(v float64)bool{return !math.IsNaN(v) && !math.IsInf(v,0)}
func checkWAV(path string,channels int)(string,error){
 st,e:=os.Lstat(path)
 if e!=nil{return "",e}
 if !st.Mode().IsRegular() || st.Mode()&os.ModeSymlink!=0 || st.Size()<44 {return "",errors.New("not a regular nonempty WAV")}
 output,e:=exec.Command("ffprobe","-v","error","-select_streams","a:0","-show_entries","stream=codec_name,sample_rate,channels","-show_entries","format=duration","-of","json",path).Output()
 if e!=nil{return "",fmt.Errorf("ffprobe: %w",e)}
 var p Probe
 if e=json.Unmarshal(output,&p);e!=nil{return "",e}
 if len(p.Streams)!=1 || p.Streams[0].Codec!="pcm_f32le" || p.Streams[0].Rate!=strconv.Itoa(rate) || p.Streams[0].Channels!=channels {return "",errors.New("wrong stream type/channel count/rate")}
 duration,e:=strconv.ParseFloat(p.Format.Duration,64)
 if e!=nil || math.Abs(duration-float64(frames)/float64(rate))>0.001 {return "",errors.New("wrong audio duration")}
 f,e:=os.Open(path);if e!=nil{return "",e};defer f.Close()
 sum:=sha256.New();if _,e=io.Copy(sum,f);e!=nil{return "",e}
 return hex.EncodeToString(sum.Sum(nil)),nil
}
func verify(root string)error{
 f,e:=os.Open(filepath.Join(root,"renderer-receipts.jsonl"));if e!=nil{return e};defer f.Close()
 read:=bufio.NewScanner(f);read.Buffer(make([]byte,2048),1024*1024)
 seen:=map[string]bool{};finish:=false
 for read.Scan(){
  line:=strings.TrimSpace(read.Text())
  if line=="spatial_native_PASS profiles=6"{finish=true;continue}
  if !strings.HasPrefix(line,"{"){return fmt.Errorf("unexpected diagnostic line %q",line)}
  var r Receipt
  if e=json.Unmarshal([]byte(line),&r);e!=nil{return e}
  if seen[r.Profile]{return errors.New("duplicate rendered profile")}
  if e=checkReceipt(r);e!=nil{return fmt.Errorf("%s: %w",r.Profile,e)}
  digest,e:=checkWAV(filepath.Join(root,r.WAV),r.Channels);if e!=nil{return fmt.Errorf("%s: %w",r.Profile,e)}
  seen[r.Profile]=true
  fmt.Printf("spatial_profile_PASS %s channels=%d peak=%.6f sha256=%s\n",r.Profile,r.Channels,r.Peak,digest)
 }
 if e=read.Err();e!=nil{return e}
 if !finish || len(seen)!=len(expected){return fmt.Errorf("incomplete renderer admission %d/%d",len(seen),len(expected))}
 fmt.Println("spatial_qualification_PASS profiles=6 48000Hz float32 native layout: channel identity separately qualified")
 return nil
}
func main(){
 if len(os.Args)!=2 {fmt.Fprintln(os.Stderr,"usage: verify OUTPUT_DIR");os.Exit(2)}
 if e:=verify(os.Args[1]);e!=nil{fmt.Fprintln(os.Stderr,"SPATIAL_FIRST_FAILURE",e);os.Exit(1)}
}
