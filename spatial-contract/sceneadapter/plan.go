// Package sceneadapter records source-owned scene identity, ENU pose and
// explicit, optional renderer-independent amplitude policy decisions.
// It does not implement panning, Doppler, HRTF, room acoustics or a transport.
package sceneadapter

import (
 "crypto/sha256"
 "encoding/hex"
 "errors"
 "math"
 "regexp"
 "strconv"
 "strings"
 "example.invalid/spatial-contract/attenuation"
)
var ErrScene=errors.New("spatial scene: invalid identity/rights/clock/geometry/channel metadata")
var idPattern=regexp.MustCompile(`^[a-z][a-z0-9_-]{2,63}$`)
type Position struct{ East, North, Up float64 }
type ChannelLayout string
const (
 Stereo ChannelLayout="stereo"
 Surround51 ChannelLayout="surround_5_1"
 Surround71 ChannelLayout="surround_7_1"
)
func (l ChannelLayout) Channels() int {
 switch l {case Stereo:return 2;case Surround51:return 6;case Surround71:return 8}
 return 0
}
func (l ChannelLayout) Labels() []string {
 switch l {
 case Stereo:return []string{"FL","FR"}
 case Surround51:return []string{"FL","FR","FC","LFE","SL","SR"}
 case Surround71:return []string{"FL","FR","FC","LFE","SL","SR","BL","BR"}
 }
 return nil
}
type Scene struct {
 SourceID string
 ListenerID string
 Rights string
 OriginalSourceSHA256 string
 RateHz int
 StartFrame int64
 FrameCount int
 Emitter Position
 Listener Position
 Layout ChannelLayout
 Envelope attenuation.Envelope
}
// Stable and original-only rights categories for public CI. No private identity.
const OriginalRights="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC"
func validPosition(p Position) bool{
 return !math.IsNaN(p.East)&&!math.IsInf(p.East,0)&&!math.IsNaN(p.North)&&!math.IsInf(p.North,0)&&!math.IsNaN(p.Up)&&!math.IsInf(p.Up,0)
}
func (s Scene) Validate() error {
 if !idPattern.MatchString(s.SourceID) || !idPattern.MatchString(s.ListenerID) ||
  s.SourceID==s.ListenerID || s.Rights!=OriginalRights ||
  len(s.OriginalSourceSHA256)!=64 || strings.Trim(s.OriginalSourceSHA256,"0123456789abcdef")!="" ||
  s.RateHz!=48000 || s.StartFrame<0 || s.FrameCount<=0 || s.FrameCount>48000*10 ||
  s.Layout.Channels()==0 || !validPosition(s.Emitter)||!validPosition(s.Listener)||
  s.Envelope.Validate()!=nil {return ErrScene}
 dx:=s.Emitter.East-s.Listener.East
 dy:=s.Emitter.North-s.Listener.North
 dz:=s.Emitter.Up-s.Listener.Up
 d:=math.Hypot(math.Hypot(dx,dy),dz)
 if math.IsNaN(d)||math.IsInf(d,0)||d<=0{return ErrScene}
 return nil
}
type Decision struct {
 Schema string `json:"schema"`
 RenderID string `json:"render_id"`
 SourceID string `json:"source_id"`
 ListenerID string `json:"listener_id"`
 OriginalSourceSHA256 string `json:"original_source_sha256"`
 Rights string `json:"rights"`
 RateHz int `json:"rate_hz"`
 StartFrame int64 `json:"start_frame"`
 FrameCount int `json:"frame_count"`
 Layout string `json:"layout"`
 ChannelLabels []string `json:"channel_labels"`
 CoordinateSystem string `json:"coordinate_system"`
 DistanceMeters float64 `json:"distance_meters"`
 Curve string `json:"curve"`
 Gain float64 `json:"gain"`
 Capabilities []string `json:"capabilities"`
}
// Plan is stable for the exact source identity, frame index and coordinates.
// The hash is a deterministic planning key, never a replacement for source
// SHA or a signature. Float representation uses Go's exact round-trip format.
func Plan(s Scene) (Decision,error){
 if err:=s.Validate();err!=nil{return Decision{},err}
 dx:=s.Emitter.East-s.Listener.East
 dy:=s.Emitter.North-s.Listener.North
 dz:=s.Emitter.Up-s.Listener.Up
 distance:=math.Hypot(math.Hypot(dx,dy),dz)
 gain,err:=s.Envelope.Gain(distance)
 if err!=nil{return Decision{},err}
 parts:=[]string{"spatial_audio.scene_plan.v1",s.SourceID,s.ListenerID,
  s.OriginalSourceSHA256,strconv.FormatInt(s.StartFrame,10),
  strconv.Itoa(s.FrameCount),strconv.Itoa(s.RateHz),
  string(s.Layout),string(s.Envelope.Curve),
  floatToken(s.Envelope.ReferenceMeters),floatToken(s.Envelope.MinimumMeters),
  floatToken(s.Emitter.East),floatToken(s.Emitter.North),floatToken(s.Emitter.Up),
  floatToken(s.Listener.East),floatToken(s.Listener.North),floatToken(s.Listener.Up)}
 hash:=sha256.Sum256([]byte(strings.Join(parts,"|")))
 return Decision{Schema:"spatial_audio.scene_plan.v1",RenderID:hex.EncodeToString(hash[:]),
  SourceID:s.SourceID,ListenerID:s.ListenerID,Rights:s.Rights,
  OriginalSourceSHA256:s.OriginalSourceSHA256,RateHz:s.RateHz,
  StartFrame:s.StartFrame,FrameCount:s.FrameCount,Layout:string(s.Layout),
  ChannelLabels:s.Layout.Labels(),CoordinateSystem:"ENU_METERS",
  DistanceMeters:distance,Curve:string(s.Envelope.Curve),Gain:gain,
  Capabilities:[]string{"PCM_AMPLITUDE_ENVELOPE_ONLY","NO_SPATIAL_PANNING","NO_ROOM","NO_DOPPLER",
   "NO_ACOUSTIC_DELAY","NO_HRTF","NO_SAMPLE_CONTINUOUS_6DOF"}},nil
}
func floatToken(v float64) string {return strconv.FormatFloat(v,'g',17,64)}
// Apply consumes distinct, already-panned interleaved source PCM and returns a
// newly allocated output; source cannot be clobbered by this adapter.
func Apply(s Scene,source []float32) ([]float32,Decision,error){
 plan,err:=Plan(s);if err!=nil{return nil,Decision{},err}
 if len(source)!=s.FrameCount*s.Layout.Channels(){return nil,Decision{},ErrScene}
 dst:=make([]float32,len(source))
 if err=attenuation.ApplyInterleaved(dst,source,s.Layout.Channels(),plan.Gain,plan.Gain);err!=nil{
  return nil,Decision{},err
 }
 return dst,plan,nil
}
