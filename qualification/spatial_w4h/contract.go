package main

// W4h public self-authored synthetic annotations only; no ASR, emotion inference or real speaker.
import (
 "bytes"
 "crypto/sha256"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "math"
 "sort"
)
const rate int64=48000
const rights="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC"
const schema="scp.av_presentation.v1"
type Clock struct { AudioHz int64 `json:"audio_hz"`; FPSNum int64 `json:"fps_num"`; FPSDen int64 `json:"fps_den"`; DurationSamples int64 `json:"duration_samples"` }
type Cue struct { ID string `json:"id"`; Kind string `json:"kind"`; Stream string `json:"stream"`; Origin string `json:"origin"`; StartSample int64 `json:"start_sample"`; EndSample int64 `json:"end_sample"`; Value string `json:"value"` }
type Pose struct { Stream string `json:"stream"`; Sample int64 `json:"sample"`; Value float64 `json:"value"`; Discontinuity bool `json:"discontinuity"` }
type Packet struct { Schema string `json:"schema"`; Rights string `json:"rights"`; SourceSHA256 string `json:"source_sha256"`; Clock Clock `json:"clock"`; Cues []Cue `json:"cues"`; Poses []Pose `json:"poses"` }
type Receipt struct { Schema string `json:"schema"`; Status string `json:"status"`; SourceSHA256 string `json:"source_sha256"`; PacketSHA256 string `json:"packet_sha256"`; CueCount int `json:"cue_count"`; Frames map[string]int64 `json:"start_frames"`; MidPose float64 `json:"mid_pose"`; Scope string `json:"scope"` }
func frameAt(c Clock,s int64)(int64,error){
 if s<0||s>=c.DurationSamples{return 0,errors.New("SAMPLE_OUTSIDE_PRESENTATION")}
 return (s*c.FPSNum)/(rate*c.FPSDen),nil
}
func validSHA(s string)bool{
 if len(s)!=64{return false};for _,r:=range s{if !((r>='0'&&r<='9')||(r>='a'&&r<='f')){return false}};return true
}
func Validate(p Packet)error{
 if p.Schema!=schema||p.Rights!=rights||!validSHA(p.SourceSHA256){return errors.New("SOURCE_RIGHTS_OR_ID")}
 c:=p.Clock
 if c.AudioHz!=rate||c.DurationSamples<=0||c.DurationSamples>rate*600{return errors.New("CLOCK_OUTSIDE_BOUNDS")}
 if !((c.FPSNum==24&&c.FPSDen==1)||(c.FPSNum==30&&c.FPSDen==1)||(c.FPSNum==30000&&c.FPSDen==1001)){return errors.New("VIDEO_RATE_UNSUPPORTED")}
 if len(p.Cues)==0||len(p.Cues)>4096||len(p.Poses)>4096{return errors.New("COUNT_OUTSIDE_BOUNDS")}
 ids:=map[string]bool{};lastEnd:=map[string]int64{}
 for _,e:=range p.Cues{
  if e.ID==""||ids[e.ID]||e.Stream==""||e.Value==""{return errors.New("CUE_ID_STREAM_VALUE")};ids[e.ID]=true
  switch e.Kind{case "dialogue","phoneme","viseme","expression","gesture","camera","foot_contact":default:return errors.New("CUE_KIND")}
  if e.Origin!="externally_annotated"&&e.Origin!="inferred_unverified"{return errors.New("ANNOTATION_ORIGIN")}
  if e.StartSample<0||e.EndSample<=e.StartSample||e.EndSample>c.DurationSamples{return errors.New("CUE_INTERVAL")}
  if e.Stream=="ground_truth"&&e.Origin!="externally_annotated"{return errors.New("INFERENCE_NOT_GROUND_TRUTH")}
  if e.Kind=="phoneme"||e.Kind=="viseme"{
   k:=e.Kind+"/"+e.Stream;if v,ok:=lastEnd[k];ok&&e.StartSample<v{return errors.New("OVERLAPPING_LINGUISTIC_CUES")};lastEnd[k]=e.EndSample
  }
 }
 previous:=map[string]int64{};observed:=map[string]bool{}
 for _,k:=range p.Poses{
  if k.Stream==""||math.IsNaN(k.Value)||math.IsInf(k.Value,0)||k.Value<0||k.Value>1||k.Sample<0||k.Sample>=c.DurationSamples{return errors.New("POSE_RANGE")}
  if observed[k.Stream]&&k.Sample<=previous[k.Stream]{return errors.New("POSE_NONMONOTONIC")}
  previous[k.Stream]=k.Sample;observed[k.Stream]=true
 }
 return nil
}
// encoding/json permits duplicate keys by default; independently reject before typed decode.
func rejectDuplicateKeys(b []byte)error{
 dec:=json.NewDecoder(bytes.NewReader(b))
 var scan func()error
 scan=func()error{
  tok,err:=dec.Token();if err!=nil{return err}
  delim,ok:=tok.(json.Delim);if !ok{return nil}
  switch delim{
  case '{':
   seen:=map[string]bool{}
   for dec.More(){
    t,err:=dec.Token();if err!=nil{return err}
    k,ok:=t.(string);if !ok||seen[k]{return errors.New("DUPLICATE_OR_INVALID_JSON_KEY")};seen[k]=true
    if err:=scan();err!=nil{return err}
   }
   _,err:=dec.Token();return err
  case '[':
   for dec.More(){if err:=scan();err!=nil{return err}}
   _,err:=dec.Token();return err
  default:return errors.New("UNEXPECTED_JSON_DELIMITER")
  }
 }
 if err:=scan();err!=nil{return err}
 var trailing any;if dec.Decode(&trailing)!=io.EOF{return errors.New("TRAILING_JSON")}
 return nil
}
func Decode(b []byte)(Packet,error){
 if e:=rejectDuplicateKeys(b);e!=nil{return Packet{},e}
 var p Packet;dec:=json.NewDecoder(bytes.NewReader(b));dec.DisallowUnknownFields()
 if e:=dec.Decode(&p);e!=nil{return Packet{},e}
 var trailing any;if e:=dec.Decode(&trailing);e!=io.EOF{return Packet{},errors.New("TRAILING_JSON")}
 return p,Validate(p)
}
// Interpolate only within source-annotated continuous span, with hard step at declared cut.
func PoseAt(p Packet,stream string,s int64)(float64,error){
 if e:=Validate(p);e!=nil{return 0,e}
 if s<0||s>=p.Clock.DurationSamples{return 0,errors.New("SAMPLE_OUTSIDE_PRESENTATION")}
 var keys []Pose;for _,k:=range p.Poses{if k.Stream==stream{keys=append(keys,k)}}
 if len(keys)==0{return 0,errors.New("POSE_STREAM_MISSING")}
 sort.Slice(keys,func(i,j int)bool{return keys[i].Sample<keys[j].Sample})
 if s<=keys[0].Sample{return keys[0].Value,nil}
 for i:=1;i<len(keys);i++{
  if s==keys[i].Sample{return keys[i].Value,nil}
  if s<keys[i].Sample{
   if keys[i].Discontinuity{return keys[i-1].Value,nil}
   a,b:=keys[i-1],keys[i]
   return a.Value+(b.Value-a.Value)*float64(s-a.Sample)/float64(b.Sample-a.Sample),nil
  }
 }
 return keys[len(keys)-1].Value,nil
}
func sample()Packet{
 return Packet{Schema:schema,Rights:rights,SourceSHA256:fmt.Sprintf("%x",sha256.Sum256([]byte("original-synthetic-w4h-voice-source"))),Clock:Clock{rate,30000,1001,rate*2},Cues:[]Cue{
  {"word0","dialogue","ground_truth","externally_annotated",24000,36000,"self-authored-syllable"},
  {"ph0","phoneme","ground_truth","externally_annotated",24000,30000,"m"},
  {"ph1","phoneme","ground_truth","externally_annotated",30000,36000,"a"},
  {"vi0","viseme","mouth","externally_annotated",24000,30000,"closed"},
  {"vi1","viseme","mouth","externally_annotated",30000,36000,"open"},
  {"expr0","expression","face","externally_annotated",22000,38000,"neutral_to_alert"},
  {"gest0","gesture","arm","externally_annotated",28000,32000,"beat"},
  {"cam0","camera","camera","externally_annotated",0,48000,"front"},
  {"foot0","foot_contact","left_sole","externally_annotated",24000,24001,"synthetic_contact"},
 },Poses:[]Pose{
  {"jaw",0,0,false},{"jaw",24000,0,false},{"jaw",30000,1,false},
  {"jaw",36000,0,true},{"jaw",48000,0,false},
 }}
}
func MakeReceipt(p Packet)(Receipt,error){
 if e:=Validate(p);e!=nil{return Receipt{},e}
 raw,e:=json.Marshal(p);if e!=nil{return Receipt{},e}
 frames:=map[string]int64{}
 for _,cue:=range p.Cues{f,e:=frameAt(p.Clock,cue.StartSample);if e!=nil{return Receipt{},e};frames[cue.ID]=f}
 v,e:=PoseAt(p,"jaw",27000);if e!=nil{return Receipt{},e}
 return Receipt{Schema:"scp.w4h_annotated_sync_receipt.v1",Status:"SOURCE_ONLY_TYPED_ANNOTATION_PASS",SourceSHA256:p.SourceSHA256,PacketSHA256:fmt.Sprintf("%x",sha256.Sum256(raw)),CueCount:len(p.Cues),Frames:frames,MidPose:v,Scope:"ANNOTATION_ONLY_NO_ASR_NO_EMOTION_INFERENCE_NO_NATIVE_MEDIA"},nil
}
