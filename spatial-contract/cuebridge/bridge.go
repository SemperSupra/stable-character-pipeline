// Package cuebridge maps owner-annotated contact/dialogue/phoneme/gesture
// events onto the existing spatial_audio.v1 canonical source transport.
// It does not infer motion, speech, phonemes, visemes, or provide DSP.
package cuebridge

import (
 "bytes"
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "errors"
 "fmt"
 "regexp"
 "sort"
 "example.invalid/spatial-contract/avsync"
 "example.invalid/spatial-contract/contract"
)

var ErrCue=errors.New("avsync cuebridge: invalid source/cue/rights/transport")
var labelPattern=regexp.MustCompile(`^[A-Za-z0-9_.-]{1,32}$`)
const Rights="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC"

type Annotation struct {
 ID string `json:"id"`
 EmitterID string `json:"emitter_id"`
 Kind avsync.EventKind `json:"kind"`
 Label string `json:"label"`
 AtSample int64 `json:"at_sample"`
}
type Cue struct {
 ID string `json:"id"`
 EmitterID string `json:"emitter_id"`
 Kind avsync.EventKind `json:"kind"`
 Label string `json:"label"`
 SceneSample int64 `json:"scene_sample"`
 SourceSample int64 `json:"source_sample"`
 VideoFrame int64 `json:"video_frame_containing_sample"`
 OriginalWAVSHA256 string `json:"original_wav_sha256"`
}
type Receipt struct {
 Schema string `json:"schema"`
 CanonicalSceneSHA256 string `json:"canonical_scene_sha256"`
 Rate avsync.Rate `json:"rate"`
 SourceRights string `json:"source_rights"`
 Cues []Cue `json:"cues"`
 Limitations []string `json:"limitations"`
}
// Only canonical PCM16 mono 48k RIFF with a conventional 44-byte header is
// supported: no hidden resampling, WAV chunk guessing or ignored metadata.
func validatedWAV(b []byte)(int64,error){
 if len(b)<44||!bytes.Equal(b[:4],[]byte("RIFF"))||
  !bytes.Equal(b[8:16],[]byte("WAVEfmt "))||
  !bytes.Equal(b[36:40],[]byte("data"))||
  binary.LittleEndian.Uint32(b[4:])!=uint32(len(b)-8)||
  binary.LittleEndian.Uint32(b[16:])!=16||
  binary.LittleEndian.Uint16(b[20:])!=1||
  binary.LittleEndian.Uint16(b[22:])!=1||
  binary.LittleEndian.Uint32(b[24:])!=48000||
  binary.LittleEndian.Uint32(b[28:])!=96000||
  binary.LittleEndian.Uint16(b[32:])!=2||
  binary.LittleEndian.Uint16(b[34:])!=16||
  binary.LittleEndian.Uint32(b[40:])!=uint32(len(b)-44)||
  (len(b)-44)%2!=0{return 0,ErrCue}
 return int64((len(b)-44)/2),nil
}
func allowedKind(k avsync.EventKind)bool{
 switch k{
 case avsync.FootContact,avsync.DialogueStart,avsync.PhonemeBoundary,avsync.GestureBeat:return true
 default:return false
 }
}
// Build computes source-sample offsets without moving the canonical scene
// event PTS. Clip-relative seek is explicit and relative to gate start.
func Build(s contract.Scene, files map[string][]byte, anns []Annotation,rate avsync.Rate,rights string)(Receipt,error){
 sceneSHA,err:=s.Admission(true)
 if err!=nil||rate.Validate()!=nil||rights!=Rights{return Receipt{},ErrCue}
 if len(anns)==0||len(anns)>4096{return Receipt{},ErrCue}
 durations:=map[string]int64{}
 hashes:=map[string]string{}
 emitters:=map[string]contract.Emitter{}
 for _,e:=range s.Emitters{
  b,ok:=files[e.ID];if !ok{return Receipt{},fmt.Errorf("%w: missing emitter %q",ErrCue,e.ID)}
  frames,err:=validatedWAV(b);if err!=nil{return Receipt{},err}
  h:=sha256.Sum256(b);digest:=hex.EncodeToString(h[:])
  if digest!=e.AssetSHA256{return Receipt{},fmt.Errorf("%w: source SHA mismatch %q",ErrCue,e.ID)}
  durations[e.ID]=frames;hashes[e.ID]=digest;emitters[e.ID]=e
 }
 results:=make([]Cue,0,len(anns))
 ids:=map[string]bool{}
 for _,a:=range anns{
  if !labelPattern.MatchString(a.ID)||!labelPattern.MatchString(a.EmitterID)||
   !labelPattern.MatchString(a.Label)||!allowedKind(a.Kind)||ids[a.ID]||
   a.AtSample<0||a.AtSample>=int64(s.DurationMS)*48{return Receipt{},ErrCue}
  ids[a.ID]=true
  e,ok:=emitters[a.EmitterID];if !ok{return Receipt{},ErrCue}
  start,stop:=int64(e.SourceStartFrame),int64(e.SourceStopFrame)
  if stop==0{stop=int64(s.DurationMS)*48}
  if a.AtSample<start||a.AtSample>=stop{return Receipt{},ErrCue}
  offset:=a.AtSample
  switch e.SourceTransport{
   case "","scene_locked":
     if e.SourceOffsetFrame!=0{return Receipt{},ErrCue}
   case "clip_relative":
     offset=a.AtSample-start+int64(e.SourceOffsetFrame)
   default:return Receipt{},ErrCue
  }
  if offset<0||offset>=durations[a.EmitterID]{
   return Receipt{},fmt.Errorf("%w: seek outside original source",ErrCue)
  }
  videoFrame,err:=avsync.FrameContainingSample(a.AtSample,rate)
  if err!=nil{return Receipt{},err}
  results=append(results,Cue{ID:a.ID,EmitterID:e.ID,Kind:a.Kind,Label:a.Label,
   SceneSample:a.AtSample,SourceSample:offset,VideoFrame:videoFrame,
   OriginalWAVSHA256:hashes[e.ID]})
 }
 sort.Slice(results,func(i,j int)bool{
  if results[i].SceneSample!=results[j].SceneSample{return results[i].SceneSample<results[j].SceneSample}
  return results[i].ID<results[j].ID
 })
 return Receipt{Schema:"spatial_audio.annotated_cues.v1",CanonicalSceneSHA256:sceneSHA,
  Rate:rate,SourceRights:rights,Cues:results,
  Limitations:[]string{"ANNOTATIONS_ARE_EXTERNAL_GROUND_TRUTH","NO_PHONEME_RECOGNITION",
   "NO_VISEME_INFERENCE","NO_FOOT_CONTACT_DETECTION","NO_AUDIO_RENDERING",
   "NO_HUMAN_PERCEPTUAL_LIPSYNC","NO_SOURCE_TIME_STRETCH"}},nil
}
