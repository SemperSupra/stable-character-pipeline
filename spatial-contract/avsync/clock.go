// Package avsync maps *presentation* timestamps onto canonical 48k audio
// samples without accumulating floating-point or rounded video-frame deltas.
// It is a scheduling/manifest layer; it does not encode, resample, or play PCM.
package avsync

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "math"
 "regexp"
)

const AudioHz int64 = 48000
const MaxDurationSamples int64 = 48000*60*60*10 // bounded 10-hour research timeline
var ErrClock=errors.New("avsync: invalid clock/event/rights")
var validID=regexp.MustCompile(`^[a-z][a-z0-9_-]{2,63}$`)
var validSHA=regexp.MustCompile(`^[0-9a-f]{64}$`)

type Rate struct{ Num, Den int64 }
func (r Rate) Validate()error {
 if r.Num<1||r.Den<1||r.Num>240000||r.Den>1001||
  float64(r.Num)/float64(r.Den)>240||float64(r.Num)/float64(r.Den)<1 {return ErrClock}
 return nil
}
// Seconds is an exact rational, in reduced terms only when requested.
// In particular 30000/1001 FPS frame #1 = 1001/30000 seconds, NOT
// a truncated constant number of 48k sample frames.
type Seconds struct{ Numerator, Denominator int64 }
func FramePTS(frame int64,rate Rate)(Seconds,error){
 if err:=rate.Validate();err!=nil||frame<0||frame>240*60*60*10{return Seconds{},ErrClock}
 return Seconds{Numerator:frame*rate.Den,Denominator:rate.Num},nil
}
func SamplePTS(sample int64)(Seconds,error){
 if sample<0||sample>MaxDurationSamples{return Seconds{},ErrClock}
 return Seconds{Numerator:sample,Denominator:AudioHz},nil
}
func frameNumerator(frame int64,rate Rate)(int64,error){
 if err:=rate.Validate();err!=nil||frame<0||frame>240*60*60*10{return 0,ErrClock}
 // Exact bounded multiplication; safety bound < 2^63.
 return frame*rate.Den*AudioHz,nil
}
func SampleFloor(frame int64,rate Rate)(int64,error){
 n,err:=frameNumerator(frame,rate);if err!=nil{return 0,err}
 v:=n/rate.Num
 if v>MaxDurationSamples{return 0,ErrClock};return v,nil
}
func SampleCeil(frame int64,rate Rate)(int64,error){
 n,err:=frameNumerator(frame,rate);if err!=nil{return 0,err}
 v:=n/rate.Num;if n%rate.Num!=0{v++}
 if v>MaxDurationSamples{return 0,ErrClock};return v,nil
}
func SampleNearest(frame int64,rate Rate)(int64,error){
 n,err:=frameNumerator(frame,rate);if err!=nil{return 0,err}
 v:=n/rate.Num
 if n%rate.Num*2>=rate.Num{v++}
 if v>MaxDurationSamples{return 0,ErrClock};return v,nil
}
// Audio samples are never quantized via video frame indexes. This function
// is used solely to locate the video frame whose [PTS,nextPTS) contains a
// known audio event, e.g. a foot-contact audio cue at an arbitrary sample.
func FrameContainingSample(sample int64,rate Rate)(int64,error){
 if err:=rate.Validate();err!=nil||sample<0||sample>MaxDurationSamples{return 0,ErrClock}
 denom:=AudioHz*rate.Den
 return sample*rate.Num/denom,nil
}
func MillisecondsToSamples(ms int64)(int64,error){
 if ms<0||ms>MaxDurationSamples/48{return 0,ErrClock}
 return ms*48,nil
}
type EventKind string
const(
 DialogueStart EventKind="dialogue_start"
 PhonemeBoundary EventKind="phoneme_boundary"
 FootContact EventKind="foot_contact"
 GestureBeat EventKind="gesture_beat"
 CameraCut EventKind="camera_cut"
)
type Event struct {
 ID string `json:"id"`
 SourceID string `json:"source_id"`
 Kind EventKind `json:"kind"`
 AtSample int64 `json:"at_sample"`
 SourceSHA256 string `json:"source_sha256"`
}
type Manifest struct {
 Schema string `json:"schema"`
 Clock string `json:"clock"`
 AudioSampleHz int64 `json:"audio_sample_hz"`
 VideoRate Rate `json:"video_rate"`
 AudioSamples int64 `json:"audio_samples"`
 VideoFrames int64 `json:"video_frames"`
 Events []Event `json:"events"`
 LatencySamples int64 `json:"latency_samples"`
 TailSamples int64 `json:"tail_samples"`
 Rights string `json:"rights"`
}
func (m Manifest) Validate()error{
 if m.Schema!="spatial_audio.avsync.v1"||m.Clock!="PTS_ZERO_COMMON_TIMELINE"||
  m.AudioSampleHz!=AudioHz||m.Rights!="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC"||
  m.VideoRate.Validate()!=nil||m.AudioSamples<=0||m.AudioSamples>MaxDurationSamples||
  m.VideoFrames<=0||m.LatencySamples<0||m.TailSamples<0||
  m.LatencySamples>AudioHz*10||m.TailSamples>AudioHz*30{return ErrClock}
 end,err:=SampleNearest(m.VideoFrames,m.VideoRate)
 if err!=nil||int64(math.Abs(float64(end-m.AudioSamples)))>1{return ErrClock}
 ids:=map[string]bool{}
 for _,e:=range m.Events{
  if !validID.MatchString(e.ID)||!validID.MatchString(e.SourceID)||
    !validSHA.MatchString(e.SourceSHA256)||e.AtSample<0||e.AtSample>=m.AudioSamples||
    ids[e.ID]{return ErrClock}
  ids[e.ID]=true
  switch e.Kind{case DialogueStart,PhonemeBoundary,FootContact,GestureBeat,CameraCut:
   default:return ErrClock}
 }
 return nil
}
func (m Manifest) Digest()(string,error){
 if err:=m.Validate();err!=nil{return "",err}
 b,err:=json.Marshal(m);if err!=nil{return "",fmt.Errorf("%w: %v",ErrClock,err)}
 h:=sha256.Sum256(b);return hex.EncodeToString(h[:]),nil
}
// Output alignment policy: if the DSP adds a measured delay, *do not*
// move canonical event samples. An export must explicitly trim the
// measured leading latency before muxing, and retain an explicitly bounded
// tail (or fail). Unknown or variable DSP latency cannot be claimed sync.
func (m Manifest) RequiredTrim() (int64,error){
 if err:=m.Validate();err!=nil{return 0,err}
 return m.LatencySamples,nil
}
