// Package canonicalbridge is an opt-in, loss-declared adapter from the
// existing authoritative spatial_audio.v1 contract to the already qualified
// Go sceneadapter gain-only scene. It is NOT a replacement scene authority.
package canonicalbridge

import(
 "bytes"
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "errors"
 "fmt"
 "math"
 "example.invalid/spatial-contract/attenuation"
 "example.invalid/spatial-contract/contract"
 "example.invalid/spatial-contract/sceneadapter"
)
var ErrUnsupported=errors.New("spatial canonical bridge: unqualified scene/media/transport")
type Evidence struct{
 Schema string `json:"schema"`
 CanonicalSceneSHA256 string `json:"canonical_scene_sha256"`
 SourceWAVSHA256 string `json:"source_wav_sha256"`
 OriginalRights string `json:"original_rights"`
 SourceTransport string `json:"source_transport"`
 CanonicalChannelLabels []string `json:"canonical_channel_labels"`
 AdaptedChannelLabels []string `json:"adapted_channel_labels"`
 Timebase string `json:"timebase"`
 MotionInterpolation string `json:"motion_interpolation"`
 OmittedCapabilities []string `json:"omitted_capabilities"`
}
func validOriginalPCM16MonoWAV(wav []byte) (int,error){
 if len(wav)<44 || !bytes.Equal(wav[0:4],[]byte("RIFF")) ||
  !bytes.Equal(wav[8:16],[]byte("WAVEfmt "))||
  !bytes.Equal(wav[36:40],[]byte("data"))||
  binary.LittleEndian.Uint32(wav[16:])!=16||
  binary.LittleEndian.Uint16(wav[20:])!=1||
  binary.LittleEndian.Uint16(wav[22:])!=1||
  binary.LittleEndian.Uint32(wav[24:])!=48000||
  binary.LittleEndian.Uint32(wav[28:])!=96000||
  binary.LittleEndian.Uint16(wav[32:])!=2||
  binary.LittleEndian.Uint16(wav[34:])!=16||
  binary.LittleEndian.Uint32(wav[4:])!=uint32(len(wav)-8)||
  binary.LittleEndian.Uint32(wav[40:])!=uint32(len(wav)-44)||
  (len(wav)-44)%2!=0{return 0,ErrUnsupported}
 return (len(wav)-44)/2,nil
}
func interpolate(keys []contract.Key,frame int64) (sceneadapter.Position,error){
 t:=float64(frame)/48.0
 if len(keys)==0||t<0{return sceneadapter.Position{},ErrUnsupported}
 if t<=float64(keys[0].TimeMS){
  v:=keys[0].Position
  return sceneadapter.Position{East:v.X,North:v.Y,Up:v.Z},nil
 }
 for i:=1;i<len(keys);i++{
  if t<=float64(keys[i].TimeMS){
   a,b:=keys[i-1],keys[i]
   alpha:=(t-float64(a.TimeMS))/float64(b.TimeMS-a.TimeMS)
   return sceneadapter.Position{
    East:a.Position.X+alpha*(b.Position.X-a.Position.X),
    North:a.Position.Y+alpha*(b.Position.Y-a.Position.Y),
    Up:a.Position.Z+alpha*(b.Position.Z-a.Position.Z)},nil
  }
 }
 v:=keys[len(keys)-1].Position
 return sceneadapter.Position{East:v.X,North:v.Y,Up:v.Z},nil
}
// Plan converts one canonical emitter/output at one frame. The WAV is read
// and SHA-checked here, but this bridge does not render, seek or resample it.
// Only selected visible stereo and 5.1/7.1 speaker outputs are admitted;
// binaural, 2.1 bass management and height profiles remain UNSUPPORTED.
func Plan(c contract.Scene,emitterID,outputID string,wav []byte,
 originalRights string,sceneFrame int64,frames int,env attenuation.Envelope)(
 sceneadapter.Scene,sceneadapter.Decision,Evidence,error){
 digest,err:=c.Admission(true)
 if err!=nil{return sceneadapter.Scene{},sceneadapter.Decision{},Evidence{},fmt.Errorf("%w: %v",ErrUnsupported,err)}
 if originalRights!=sceneadapter.OriginalRights{return sceneadapter.Scene{},sceneadapter.Decision{},Evidence{},ErrUnsupported}
 assetFrames,err:=validOriginalPCM16MonoWAV(wav)
 if err!=nil{return sceneadapter.Scene{},sceneadapter.Decision{},Evidence{},err}
 var emitter *contract.Emitter
 for i:=range c.Emitters{if c.Emitters[i].ID==emitterID{emitter=&c.Emitters[i];break}}
 var output *contract.Output
 for i:=range c.Outputs{if c.Outputs[i].ID==outputID{output=&c.Outputs[i];break}}
 if emitter==nil||output==nil||frames<=0||sceneFrame<0{return sceneadapter.Scene{},sceneadapter.Decision{},Evidence{},ErrUnsupported}
 sha:=sha256.Sum256(wav)
 sourceHash:=hex.EncodeToString(sha[:])
 if sourceHash!=emitter.AssetSHA256{return sceneadapter.Scene{},sceneadapter.Decision{},Evidence{},ErrUnsupported}
 if emitter.SourceTransport!=""&&emitter.SourceTransport!="scene_locked" {
  return sceneadapter.Scene{},sceneadapter.Decision{},Evidence{},ErrUnsupported
 }
 // No pretending to admit clip-relative offsets, mute windows or source seek:
 // only scene-locked source, aligned at frame 0, with fully available WAV data.
 start:=emitter.SourceStartFrame
 stop:=emitter.SourceStopFrame
 if stop==0{stop=c.DurationMS*48}
 if sceneFrame<int64(start)||sceneFrame+int64(frames)>int64(stop)||
  sceneFrame+int64(frames)>int64(assetFrames)||sceneFrame+int64(frames)>int64(c.DurationMS*48){
  return sceneadapter.Scene{},sceneadapter.Decision{},Evidence{},ErrUnsupported
 }
 var layout sceneadapter.ChannelLayout
 switch output.Profile{
 case "stereo":
  if len(output.Channels)!=2||output.Channels[0]!="L"||output.Channels[1]!="R" {return sceneadapter.Scene{},sceneadapter.Decision{},Evidence{},ErrUnsupported}
  layout=sceneadapter.Stereo
 case "surround_5_1":layout=sceneadapter.Surround51
 case "surround_7_1":layout=sceneadapter.Surround71
 default:return sceneadapter.Scene{},sceneadapter.Decision{},Evidence{},ErrUnsupported
 }
 pos,err:=interpolate(emitter.Motion,sceneFrame)
 if err!=nil{return sceneadapter.Scene{},sceneadapter.Decision{},Evidence{},ErrUnsupported}
 listener,err:=interpolate(c.Listener,sceneFrame)
 if err!=nil{return sceneadapter.Scene{},sceneadapter.Decision{},Evidence{},ErrUnsupported}
 if math.IsNaN(pos.East)||math.IsInf(pos.East,0){return sceneadapter.Scene{},sceneadapter.Decision{},Evidence{},ErrUnsupported}
 s:=sceneadapter.Scene{SourceID:emitter.ID,ListenerID:c.ListenerID,
  Rights:originalRights,OriginalSourceSHA256:sourceHash,RateHz:c.SampleRateHz,
  StartFrame:sceneFrame,FrameCount:frames,Emitter:pos,Listener:listener,
  Layout:layout,Envelope:env}
 d,err:=sceneadapter.Plan(s)
 if err!=nil{return sceneadapter.Scene{},sceneadapter.Decision{},Evidence{},fmt.Errorf("%w: %v",ErrUnsupported,err)}
 evidence:=Evidence{Schema:"spatial_audio.canonical_to_gain_plan.v1",
  CanonicalSceneSHA256:digest,SourceWAVSHA256:sourceHash,OriginalRights:originalRights,
  SourceTransport:"scene_locked",CanonicalChannelLabels:append([]string{},output.Channels...),
  AdaptedChannelLabels:d.ChannelLabels,
  Timebase:"CANONICAL_INTEGER_MS_KEYS_TO_EXACT_48KHZ_FRAME_QUERY",
  MotionInterpolation:"PIECEWISE_LINEAR_ENU_AT_REQUEST_FRAME",
  OmittedCapabilities:[]string{"YAW_NOT_APPLIED","DIRECTIVITY_NOT_APPLIED",
   "GAIN_DB_NOT_APPLIED","SOURCE_TRANSPORT_NOT_APPLIED","NO_SPATIAL_PANNING",
   "NO_HRTF","NO_ROOM","NO_DOPPLER"}}
 return s,d,evidence,nil
}
