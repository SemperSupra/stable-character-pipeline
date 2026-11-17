// R067: independently decode PCM WAV and enforce pre-ASR signal-integrity gates.
// An audible sound is NEVER declared speech by these nonsemantic measurements.
package main
import (
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "math"
 "os"
 "strings"
)
const sampleRate = 16000
const sampleCount = 16000
type Observation struct {
 Schema string `json:"schema"`
 SourceSHA string `json:"source_sha"`
 InputSHA string `json:"wav_sha256"`
 Status string `json:"status"`
 Expected string `json:"expected"`
 Outcome string `json:"outcome"`
 SampleRate int `json:"sample_rate_hz"`
 Samples int `json:"sample_count"`
 Peak float64 `json:"peak_linear"`
 RMS float64 `json:"rms_linear"`
 ClippedSamples int `json:"clipped_samples"`
 SignChanges int `json:"sign_changes"`
 Reason string `json:"reason,omitempty"`
 Scope string `json:"scope"`
}
func generate(name string)([]byte,error){
 if !strings.Contains("|silence|tone|breath-like-noise|clipped|truncated|","|"+name+"|"){return nil,errors.New("UNKNOWN_FIXTURE")}
 raw:=make([]byte,44+sampleCount*2)
 copy(raw[0:4],"RIFF")
 binary.LittleEndian.PutUint32(raw[4:8],uint32(len(raw)-8))
 copy(raw[8:12],"WAVE")
 copy(raw[12:16],"fmt ")
 binary.LittleEndian.PutUint32(raw[16:20],16)
 binary.LittleEndian.PutUint16(raw[20:22],1)
 binary.LittleEndian.PutUint16(raw[22:24],1)
 binary.LittleEndian.PutUint32(raw[24:28],sampleRate)
 binary.LittleEndian.PutUint32(raw[28:32],sampleRate*2)
 binary.LittleEndian.PutUint16(raw[32:34],2)
 binary.LittleEndian.PutUint16(raw[34:36],16)
 copy(raw[36:40],"data")
 binary.LittleEndian.PutUint32(raw[40:44],uint32(sampleCount*2))
 state:=uint32(137)
 for i:=0;i<sampleCount;i++{
  var sample int16
  switch name{
  case "silence","truncated":sample=0
  case "tone":sample=int16(math.Round(2800*math.Sin(2*math.Pi*440*float64(i)/sampleRate)))
  case "breath-like-noise":
   state=1664525*state+1013904223
   sample=int16(int(state>>16)%3001-1500)
  case "clipped":
   if i%2==0{sample=32767}else{sample=-32768}
  }
  binary.LittleEndian.PutUint16(raw[44+i*2:46+i*2],uint16(sample))
 }
 if name=="truncated"{return raw[:len(raw)-19],nil}
 return raw,nil
}
func decode(raw []byte)([]int16,error){
 if len(raw)<44||len(raw)>2<<20{return nil,errors.New("BOUNDED_BYTES_VIOLATION")}
 if string(raw[:4])!="RIFF"||string(raw[8:12])!="WAVE"||
    string(raw[12:16])!="fmt "||string(raw[36:40])!="data"{
  return nil,errors.New("UNSUPPORTED_WAV_HEADER")
 }
 if int(binary.LittleEndian.Uint32(raw[4:8]))!=len(raw)-8 ||
    binary.LittleEndian.Uint32(raw[16:20])!=16 ||
    binary.LittleEndian.Uint16(raw[20:22])!=1||
    binary.LittleEndian.Uint16(raw[22:24])!=1||
    binary.LittleEndian.Uint32(raw[24:28])!=sampleRate||
    binary.LittleEndian.Uint32(raw[28:32])!=sampleRate*2||
    binary.LittleEndian.Uint16(raw[32:34])!=2||
    binary.LittleEndian.Uint16(raw[34:36])!=16{
  return nil,errors.New("PCM_16KHZ_MONO_REQUIRED")
 }
 size:=int(binary.LittleEndian.Uint32(raw[40:44]))
 if size%2!=0||size<320||len(raw)!=44+size{
  return nil,errors.New("WAV_LENGTH_MISMATCH")
 }
 out:=make([]int16,size/2)
 for i:=range out{out[i]=int16(binary.LittleEndian.Uint16(raw[44+i*2:46+i*2]))}
 return out,nil
}
func inspect(samples []int16)Observation{
 r:=Observation{Schema:"scp.r067.audio-physical-veto.v1",SampleRate:sampleRate,Samples:len(samples),
  Scope:"PCM_16KHZ_MONO_SIGNAL_ONLY_NO_SPEECH_ASSERTION"}
 var sq float64
 var peak float64
 var prev int
 for i,v:=range samples{
  a:=math.Abs(float64(v)/32768)
  sq+=a*a
  if a>peak{peak=a}
  if v>=32767||v<=-32767{r.ClippedSamples++}
  sign:=0
  if v>0{sign=1}else if v<0{sign=-1}
  if i>0&&sign!=0&&prev!=0&&sign!=prev{r.SignChanges++}
  if sign!=0{prev=sign}
 }
 r.Peak=peak
 r.RMS=math.Sqrt(sq/float64(len(samples)))
 switch{
 case peak==0:r.Status="DIGITAL_SILENCE"
 case r.ClippedSamples>=64:r.Status="CLIPPED_REJECT"
 default:r.Status="AUDIO_PRESENT_UNCLASSIFIED"
 }
 return r
}
func main(){
 makeName:=flag.String("make","","one original synthetic input")
 out:=flag.String("out","","fixture WAV path")
 input:=flag.String("input","","WAV input path")
 expect:=flag.String("expect","","expected classification")
 flag.Parse()
 if *makeName!=""{
  if *out==""{fmt.Fprintln(os.Stderr,"R067_HOLD missing output");os.Exit(12)}
  raw,err:=generate(*makeName)
  if err!=nil{fmt.Fprintln(os.Stderr,"R067_HOLD",err);os.Exit(12)}
  if err:=os.WriteFile(*out,raw,0600);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(12)}
  h:=sha256.Sum256(raw)
  fmt.Printf("R067_SYNTHETIC_WAV name=%s sha256=%s bytes=%d
",*makeName,hex.EncodeToString(h[:]),len(raw))
  return
 }
 if *input==""||*expect==""{fmt.Fprintln(os.Stderr,"R067_HOLD missing input or expectation");os.Exit(12)}
 raw,err:=os.ReadFile(*input)
 r:=Observation{Schema:"scp.r067.audio-physical-veto.v1",SourceSHA:os.Getenv("GITHUB_SHA"),
  Status:"UNKNOWN",Expected:*expect,Outcome:"HOLD",Scope:"PCM_16KHZ_MONO_SIGNAL_ONLY_NO_SPEECH_ASSERTION"}
 if err==nil{
  h:=sha256.Sum256(raw);r.InputSHA=hex.EncodeToString(h[:])
  var samples []int16
  samples,err=decode(raw)
  if err==nil{
   obs:=inspect(samples)
   obs.SourceSHA=r.SourceSHA;obs.InputSHA=r.InputSHA;obs.Expected=r.Expected
   r=obs
   if r.Status==r.Expected{r.Outcome="PASS_NARROW"}else{r.Outcome="FAIL_EXPECTATION";r.Reason="MISMATCH"}
  }
 }
 if err!=nil{r.Status="UNKNOWN";r.Reason=err.Error()}
 data,_:=json.Marshal(r);fmt.Println(string(data))
 if r.Outcome!="PASS_NARROW"{os.Exit(12)}
}
