// Package audio turns admitted planned hoof-contact events into deterministic SYNTHETIC FOLEY.
// It does not claim recorded horse calls, evaluated biomechanics, or finished animal sound design.
package audio

import (
 "bytes"
 "crypto/sha256"
 "encoding/binary"
 "encoding/json"
 "errors"
 "fmt"
 "hash/fnv"
 "io"
 "math"
 "os"
)

const Rate = 48000
const Schema = "equine.contact.v1"

type Event struct {
 ActorID string `json:"actor_id"`
 Gait string `json:"gait"`
 Foot string `json:"foot"`
 Kind string `json:"kind"`
 ContactState string `json:"contact_state"`
 Surface string `json:"surface"`
 Frame int `json:"frame"`
 Sample int64 `json:"sample"`
 Source string `json:"source"`
}
type Input struct {
 Schema string `json:"schema"`
 Basis string `json:"basis"`
 ActorID string `json:"actor_id"`
 Gait string `json:"gait"`
 FPS int `json:"fps"`
 SampleRate int `json:"sample_rate"`
 FramesPerCycle int `json:"frames_per_cycle"`
 Cycles int `json:"cycles"`
 Evaluation string `json:"evaluation"`
 Events []Event `json:"events"`
}
type Receipt struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Gait string `json:"gait"`
 SampleRate int `json:"sample_rate"`
 DurationSamples int `json:"duration_samples"`
 EventCount int `json:"event_count"`
 NonzeroSamples int `json:"nonzero_samples"`
 WavSha256 string `json:"wav_sha256"`
 SourceState string `json:"source_state"`
 Biomechanics string `json:"biomechanics"`
}

func Parse(buf []byte)(Input,error){
 var r Input
 if len(buf)>1000000{return r,errors.New("input too large")}
 dec:=json.NewDecoder(bytes.NewReader(buf))
 dec.DisallowUnknownFields()
 if err:=dec.Decode(&r);err!=nil{return r,err}
 var tail any
 if err:=dec.Decode(&tail);err!=io.EOF{return r,errors.New("trailing JSON")}
 if r.Schema!=Schema||r.Basis!="SYNTHETIC_PLANNED"||
 r.Evaluation!="PLANNED_ONLY_NOT_EVALUATED_HOOF_CONTACT"||
 r.SampleRate!=Rate||r.FPS<12||r.FPS>120||Rate%r.FPS!=0||r.ActorID==""||
 r.Cycles<1||r.Cycles>16||r.FramesPerCycle<12||r.FramesPerCycle>240{
     return r,errors.New("unsupported or forged source contract")
 }
 if r.Events==nil||len(r.Events)>2048{return r,errors.New("invalid event count")}
 seen:=map[string]bool{}
 prev:=int64(-1)
 for _,ev:=range r.Events{
     if ev.ActorID!=r.ActorID||ev.Gait!=r.Gait||ev.Kind!="hoof_impact"||
     ev.ContactState!="planned_contact"||ev.Source!="SYNTHETIC_PLANNED"||
     !okFoot(ev.Foot)||!okSurface(ev.Surface)||
     ev.Frame<0||ev.Sample<0||ev.Sample!=int64(ev.Frame)*int64(Rate/r.FPS)||
     ev.Sample<prev||ev.Sample>int64(Rate*30) {
         return r,fmt.Errorf("invalid event %+v",ev)
     }
     key:=fmt.Sprintf("%d:%s",ev.Sample,ev.Foot)
     if seen[key] {return r,errors.New("duplicate impact")}
     seen[key]=true
     prev=ev.Sample
 }
 return r,nil
}
func okFoot(f string)bool{return f=="FL"||f=="FR"||f=="HL"||f=="HR"}
func okSurface(f string)bool{return f=="sand"||f=="soil"||f=="stone"||f=="grass"}
func seed(event Event) uint32{
 h:=fnv.New32a();h.Write([]byte(event.ActorID+"|"+event.Foot+"|"+event.Surface))
 return h.Sum32() ^ uint32(event.Sample)
}
func Render(in Input, seconds int) ([]byte,Receipt,error) {
 r:=Receipt{Schema:"equine.audio.v1",Mode:"SYNTHETIC_HOOF_FOLEY",Gait:in.Gait,
 SampleRate:Rate,SourceState:"SYNTHETIC_PLANNED_CONTACT_NOT_EVALUATED",
 Biomechanics:"UNKNOWN"}
 if seconds<1||seconds>30{return nil,r,errors.New("duration out of bounds")}
 // Force re-validation of a caller-constructed Input.
 body,err:=json.Marshal(in);if err!=nil{return nil,r,err}
 in,err=Parse(body);if err!=nil{return nil,r,err}
 count:=seconds*Rate
 values:=make([]float64,count)
 for _,ev:=range in.Events{
     at:=int(ev.Sample)
     if at>=count{return nil,r,errors.New("impact past end of output")}
     freq,decay,gain:=95.0,0.018,0.20
     switch ev.Surface{
     case "stone":freq,decay,gain=330,.048,.37
     case "soil":freq,decay,gain=135,.027,.22
     case "grass":freq,decay,gain=83,.014,.15
     }
     rnd:=seed(ev)
     size:=int(math.Min(float64(count-at),float64(Rate)/3))
     for i:=0;i<size;i++ {
         t:=float64(i)/Rate
         rnd^=rnd<<13;rnd^=rnd>>17;rnd^=rnd<<5
         noise:=float64(int64(rnd%65536)-32768)/32768.0
         envelope:=math.Exp(-t/decay)
         impact:=gain*envelope*(.67*math.Sin(2*math.Pi*freq*t)+.33*noise)
         values[at+i]+=impact
     }
 }
 pcm:=make([]int16,count)
 for i,x:=range values{
     if x>1{x=1};if x < -1{x=-1}
     pcm[i]=int16(math.Round(x*32767))
     if pcm[i]!=0{r.NonzeroSamples++}
 }
 var out bytes.Buffer
 out.WriteString("RIFF")
 binary.Write(&out,binary.LittleEndian,uint32(36+count*2))
 out.WriteString("WAVEfmt ")
 binary.Write(&out,binary.LittleEndian,uint32(16))
 binary.Write(&out,binary.LittleEndian,uint16(1))
 binary.Write(&out,binary.LittleEndian,uint16(1))
 binary.Write(&out,binary.LittleEndian,uint32(Rate))
 binary.Write(&out,binary.LittleEndian,uint32(Rate*2))
 binary.Write(&out,binary.LittleEndian,uint16(2))
 binary.Write(&out,binary.LittleEndian,uint16(16))
 out.WriteString("data")
 binary.Write(&out,binary.LittleEndian,uint32(count*2))
 for _,s:=range pcm {binary.Write(&out,binary.LittleEndian,s)}
 result:=out.Bytes()
 sum:=sha256.Sum256(result)
 r.WavSha256=fmt.Sprintf("%x",sum)
 r.DurationSamples=count
 r.EventCount=len(in.Events)
 return result,r,nil
}
func Write(inputPath,wavPath,receiptPath string,seconds int)error{
 b,err:=os.ReadFile(inputPath);if err!=nil{return err}
 in,err:=Parse(b);if err!=nil{return err}
 wav,rec,err:=Render(in,seconds);if err!=nil{return err}
 if err:=os.WriteFile(wavPath,wav,0644);err!=nil{return err}
 data,err:=json.MarshalIndent(rec,"","  ");if err!=nil{return err}
 return os.WriteFile(receiptPath,append(data,'\n'),0644)
}
