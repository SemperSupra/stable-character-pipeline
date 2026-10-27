// Package contract models source-independent spatial scenes before encoding.
// It is a typed interchange and admission layer; it DOES NOT spatialize audio.
package contract

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "math"
 "os"
 "path/filepath"
 "regexp"
)

const Schema="spatial_audio.v1"
const Public="PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL"
const Private="PRIVATE_FINAL_CHARACTER_VOICE"
const WorldFrame="ENU_XEast_YNorth_ZUp_m"
var idPattern=regexp.MustCompile("^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
var hashPattern=regexp.MustCompile("^[0-9a-f]{64}$")

type Vec3 struct{ X float64 `json:"x"`; Y float64 `json:"y"`; Z float64 `json:"z"` }
type Key struct {TimeMS int `json:"time_ms"`; Position Vec3 `json:"position_m"`; YawDeg float64 `json:"yaw_deg,omitempty"` }
type Emitter struct {
 ID string `json:"id"`
 Category string `json:"category"`
 AudioAsset string `json:"audio_asset"`
 AssetSHA256 string `json:"asset_sha256"`
 GainDB float64 `json:"gain_db"`
 Directivity string `json:"directivity"`
 SpreadDeg float64 `json:"spread_deg"`
 Motion []Key `json:"motion"`
 // Absolute PCM sample-frame mute gates. A zero StopFrame defaults to scene end.
 // These are NOT source-file offset seek/shift operations.
 SourceStartFrame int `json:"source_start_frame,omitempty"`
 SourceStopFrame int `json:"source_stop_frame,omitempty"`
 // Empty transport is backward-compatible scene-locked indexing.
 // Clip-relative indexes source at sceneFrame - SourceStartFrame + SourceOffsetFrame.
 SourceTransport string `json:"source_transport,omitempty"`
 SourceOffsetFrame int `json:"source_offset_frame,omitempty"`
}
type Output struct {
 ID string `json:"id"`
 Profile string `json:"profile"`
 Channels []string `json:"channels"`
 LFEPolicy string `json:"lfe_policy"`
 HRTF string `json:"hrtf,omitempty"`
}
type Scene struct {
 Schema string `json:"schema"`
 ID string `json:"id"`
 Classification string `json:"classification"`
 WorldFrame string `json:"world_frame"`
 SampleRateHz int `json:"sample_rate_hz"`
 DurationMS int `json:"duration_ms"`
 ListenerID string `json:"listener_id"`
 Listener []Key `json:"listener"`
 Emitters []Emitter `json:"emitters"`
 Outputs []Output `json:"outputs"`
}
var profiles=map[string]struct{channels []string; policy string}{
 "stereo": {[]string{"L","R"},"none"},
 "stereo_bassmanaged_2_1": {[]string{"L","R"},"bass_managed"},
 "binaural": {[]string{"EarL","EarR"},"none"},
 "surround_5_1": {[]string{"FL","FR","FC","LFE","SL","SR"},"discrete"},
 "surround_7_1": {[]string{"FL","FR","FC","LFE","SL","SR","BL","BR"},"discrete"},
 "immersive_5_1_4": {[]string{"FL","FR","FC","LFE","SL","SR","TFL","TFR","TBL","TBR"},"discrete"},
 "immersive_7_1_4": {[]string{"FL","FR","FC","LFE","SL","SR","BL","BR","TFL","TFR","TBL","TBR"},"discrete"},
}
func finite(n float64)bool{return !math.IsNaN(n)&&!math.IsInf(n,0)}
func finitePosition(v Vec3)bool{return finite(v.X)&&finite(v.Y)&&finite(v.Z)&&math.Abs(v.X)<=1e5&&math.Abs(v.Y)<=1e5&&math.Abs(v.Z)<=1e5}
func keys(keys []Key,duration int)error{
 if len(keys)==0||len(keys)>1024{return errors.New("invalid keyframe count")}
 last:=-1
 for _,k:=range keys{
  if k.TimeMS<=last || k.TimeMS<0 || k.TimeMS>=duration{return errors.New("timestamps must be strictly increasing and inside scene")}
  if !finitePosition(k.Position)||!finite(k.YawDeg)||math.Abs(k.YawDeg)>360{return errors.New("invalid position/yaw")}
  last=k.TimeMS
 }
 if keys[0].TimeMS!=0{return errors.New("initial position at time zero required")}
 return nil
}
func (s Scene)Validate()error{
 if s.Schema!=Schema || !idPattern.MatchString(s.ID)||s.WorldFrame!=WorldFrame{return errors.New("invalid schema/id/coordinate convention")}
 if s.Classification!=Public && s.Classification!=Private{return errors.New("unrecognized custody classification")}
 if s.SampleRateHz!=48000 || s.DurationMS<=0 || s.DurationMS>600000 || !idPattern.MatchString(s.ListenerID){return errors.New("unsupported timebase/duration/listener")}
 if e:=keys(s.Listener,s.DurationMS);e!=nil{return fmt.Errorf("listener: %w",e)}
 if len(s.Emitters)==0 || len(s.Emitters)>64 || len(s.Outputs)==0 || len(s.Outputs)>8{return errors.New("invalid emitter/output counts")}
 ids:=map[string]bool{s.ListenerID:true}
 cats:=map[string]bool{"human_voice":true,"robot_voice":true,"fauna":true,"alien_voice":true,"music":true,"ambience":true,"foley":true,"mechanical":true,"effects":true}
 for _,v:=range s.Emitters{
  if !idPattern.MatchString(v.ID)||ids[v.ID]||!cats[v.Category]{return fmt.Errorf("invalid/duplicate emitter %q",v.ID)}
  ids[v.ID]=true
  if !filepath.IsLocal(v.AudioAsset)||filepath.Base(v.AudioAsset)!=v.AudioAsset||filepath.Ext(v.AudioAsset)!=".wav"||!hashPattern.MatchString(v.AssetSHA256){return fmt.Errorf("unsafe WAV/hash for %q",v.ID)}
  if !finite(v.GainDB)||v.GainDB< -80||v.GainDB>12||!finite(v.SpreadDeg)||v.SpreadDeg<0||v.SpreadDeg>180 {return fmt.Errorf("invalid gain/spread for %q",v.ID)}
  if v.Directivity!="omni"&&v.Directivity!="cardioid"{return errors.New("unsupported directivity")}
  if e:=keys(v.Motion,s.DurationMS);e!=nil{return fmt.Errorf("emitter %s: %w",v.ID,e)}
  stop:=v.SourceStopFrame
  if stop==0{stop=s.DurationMS*48}
  if v.SourceStartFrame<0 || v.SourceStartFrame>=s.DurationMS*48 ||
     stop<=v.SourceStartFrame || stop>s.DurationMS*48 {
   return fmt.Errorf("invalid sample-frame source window for %q",v.ID)
  }
  switch v.SourceTransport {
  case "", "scene_locked":
   if v.SourceOffsetFrame!=0{return fmt.Errorf("offset without clip-relative transport for %q",v.ID)}
  case "clip_relative":
   if v.SourceOffsetFrame<0 || v.SourceOffsetFrame>=s.DurationMS*48 ||
      v.SourceOffsetFrame+(stop-v.SourceStartFrame)>s.DurationMS*48 {
    return fmt.Errorf("clip-relative source range exceeds admitted audio for %q",v.ID)
   }
  default:return fmt.Errorf("unqualified source transport for %q",v.ID)
  }
 }
 outputIDs:=map[string]bool{}
 for _,v:=range s.Outputs{
  expected,ok:=profiles[v.Profile]
  if !idPattern.MatchString(v.ID)||outputIDs[v.ID]||!ok{return fmt.Errorf("unrecognized/duplicate output %q",v.ID)}
  outputIDs[v.ID]=true
  if v.LFEPolicy!=expected.policy||len(v.Channels)!=len(expected.channels){return fmt.Errorf("channel/LFE policy mismatch %q",v.ID)}
  for i,ch:=range expected.channels{if v.Channels[i]!=ch{return fmt.Errorf("channel order mismatch %q %d",v.ID,i)}}
  if v.Profile=="binaural"{if v.HRTF!="builtin_mit_test"{return errors.New("binaural HRTF source not admitted")}}else if v.HRTF!=""{return errors.New("HRTF applied twice or to non-binaural output")}
 }
 return nil
}
func (s Scene)Admission(publicWorker bool)(string,error){
 if e:=s.Validate();e!=nil{return "",e}
 if publicWorker&&s.Classification!=Public{return "",errors.New("private final character content prohibited on public workers")}
 b,_:=json.Marshal(s);sum:=sha256.Sum256(b)
 return hex.EncodeToString(sum[:]),nil
}
func Load(path string)(Scene,error){
 f,e:=os.Open(path);if e!=nil{return Scene{},e};defer f.Close()
 d:=json.NewDecoder(io.LimitReader(f,1<<20));d.DisallowUnknownFields()
 var s Scene;if e=d.Decode(&s);e!=nil{return s,e}
 var extra interface{};if e=d.Decode(&extra);e!=io.EOF{return s,errors.New("trailing JSON")}
 return s,s.Validate()
}
func SyntheticFixture()Scene{
 sha:=sha256.Sum256([]byte("public fixture mono source not rendered"))
 keys:=[]Key{{TimeMS:0,Position:Vec3{X:-2,Y:5,Z:1}},{TimeMS:500,Position:Vec3{X:2,Y:5,Z:1}}}
 var outputs []Output
 for _,name:=range []string{"stereo","stereo_bassmanaged_2_1","binaural","surround_5_1","surround_7_1","immersive_5_1_4","immersive_7_1_4"}{
  p:=profiles[name];v:=Output{ID:name,Profile:name,Channels:append([]string(nil),p.channels...),LFEPolicy:p.policy}
  if name=="binaural"{v.HRTF="builtin_mit_test"}
  outputs=append(outputs,v)
 }
 return Scene{Schema:Schema,ID:"spatial_original_synthetic_fixture",Classification:Public,WorldFrame:WorldFrame,SampleRateHz:48000,DurationMS:1000,ListenerID:"listener_1",Listener:[]Key{{TimeMS:0,Position:Vec3{}}},Emitters:[]Emitter{{ID:"synthetic_robot",Category:"robot_voice",AudioAsset:"synthetic.wav",AssetSHA256:hex.EncodeToString(sha[:]),GainDB:-6,Directivity:"omni",Motion:keys}},Outputs:outputs}
}
