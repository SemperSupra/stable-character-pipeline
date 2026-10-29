package canonicalbridge
import(
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "math"
 "strings"
 "testing"
 "example.invalid/spatial-contract/attenuation"
 "example.invalid/spatial-contract/contract"
 "example.invalid/spatial-contract/sceneadapter"
)
func originalWAV()[]byte{
 n:=4800
 b:=make([]byte,44+2*n)
 copy(b[0:4],"RIFF");binary.LittleEndian.PutUint32(b[4:],uint32(len(b)-8))
 copy(b[8:16],"WAVEfmt ");binary.LittleEndian.PutUint32(b[16:],16)
 binary.LittleEndian.PutUint16(b[20:],1);binary.LittleEndian.PutUint16(b[22:],1)
 binary.LittleEndian.PutUint32(b[24:],48000);binary.LittleEndian.PutUint32(b[28:],96000)
 binary.LittleEndian.PutUint16(b[32:],2);binary.LittleEndian.PutUint16(b[34:],16)
 copy(b[36:40],"data");binary.LittleEndian.PutUint32(b[40:],uint32(2*n))
 for i:=0;i<n;i++{
  value:=int16(math.Round(.1*32767*math.Sin(2*math.Pi*410*float64(i)/48000)))
  binary.LittleEndian.PutUint16(b[44+2*i:],uint16(value))
 }
 return b
}
func fixture(wav []byte)contract.Scene{
 digest:=sha256.Sum256(wav)
 return contract.Scene{
  Schema:contract.Schema,ID:"scene_test",Classification:contract.Public,
  WorldFrame:contract.WorldFrame,SampleRateHz:48000,DurationMS:100,
  ListenerID:"listener_b",
  Listener:[]contract.Key{
   {TimeMS:0,Position:contract.Vec3{X:0,Y:0,Z:0}},
   {TimeMS:50,Position:contract.Vec3{X:1,Y:0,Z:0}}},
  Emitters:[]contract.Emitter{{
   ID:"emitter_a",Category:"foley",AudioAsset:"original.wav",
   AssetSHA256:hex.EncodeToString(digest[:]),Directivity:"omni",
   Motion:[]contract.Key{
    {TimeMS:0,Position:contract.Vec3{X:2,Y:0,Z:1}},
    {TimeMS:50,Position:contract.Vec3{X:4,Y:0,Z:1}}}}},
  Outputs:[]contract.Output{
   {ID:"speaker_a",Profile:"stereo",Channels:[]string{"L","R"},LFEPolicy:"none"},
   {ID:"speaker_b",Profile:"surround_5_1",
    Channels:[]string{"FL","FR","FC","LFE","SL","SR"},LFEPolicy:"discrete"},
  },
 }
}
func env()attenuation.Envelope{return attenuation.Envelope{
 Curve:attenuation.InverseDistance,ReferenceMeters:10,MinimumMeters:1}}
func TestCanonicalSceneAuthorityAndStereoMapping(t *testing.T){
 wav:=originalWAV();canonical:=fixture(wav)
 if err:=canonical.Validate();err!=nil{t.Fatalf("invalid canonical fixture: %v",err)}
 frame:=int64(24*48)
 s,d,e,err:=Plan(canonical,"emitter_a","speaker_a",wav,
  sceneadapter.OriginalRights,frame,1024,env())
 if err!=nil{t.Fatal(err)}
 if s.Rights!=sceneadapter.OriginalRights||s.StartFrame!=frame||
  e.CanonicalChannelLabels[0]!="L"||e.AdaptedChannelLabels[0]!="FL"||
  d.ChannelLabels[1]!="FR"{t.Fatalf("metadata mismatch %+v %+v",d,e)}
 // Keyframes linearly interpolate 24ms of 50ms, without applying yaw.
 if math.Abs(s.Emitter.East-2.96)>1e-12||math.Abs(s.Listener.East-.48)>1e-12{
  t.Fatalf("ENU interpolation %+v %+v",s.Emitter,s.Listener)
 }
 if len(d.RenderID)!=64||len(e.CanonicalSceneSHA256)!=64{t.Fatal("missing provenance")}
 _,surround,_,err:=Plan(canonical,"emitter_a","speaker_b",wav,
  sceneadapter.OriginalRights,frame,1024,env())
 if err!=nil||len(surround.ChannelLabels)!=6||surround.ChannelLabels[3]!="LFE"{
  t.Fatalf("wrong surround channel metadata %v %+v",err,surround)
 }
}
func TestRejectUnqualifiedInputs(t *testing.T){
 wav:=originalWAV()
 cases:=[]struct{name string;change func(*contract.Scene)}{
  {"private",func(s *contract.Scene){s.Classification=contract.Private}},
  {"bad_sha",func(s *contract.Scene){s.Emitters[0].AssetSHA256=strings.Repeat("f",64)}},
  {"clip_relative",func(s *contract.Scene){s.Emitters[0].SourceTransport="clip_relative"}},
  {"source_window",func(s *contract.Scene){s.Emitters[0].SourceStartFrame=1000;s.Emitters[0].SourceStopFrame=1500}},
  {"nonmono",func(s *contract.Scene){s.Emitters[0].AudioAsset="bad.ogg"}},
  {"bad_motion",func(s *contract.Scene){s.Emitters[0].Motion[1].TimeMS=0}},
  {"invalid_xyz",func(s *contract.Scene){s.Listener[0].Position.X=math.NaN()}},
  {"wrong_layout",func(s *contract.Scene){s.Outputs[0].Channels[0]="FL"}},
  {"unsupported_binaural",func(s *contract.Scene){s.Outputs[0]=contract.Output{
   ID:"speaker_a",Profile:"binaural",Channels:[]string{"EarL","EarR"},
   LFEPolicy:"none",HRTF:"builtin_mit_test"}}},
 }
 for _,tc:=range cases{
  t.Run(tc.name,func(t *testing.T){
   s:=fixture(wav);tc.change(&s)
   _,_,_,err:=Plan(s,"emitter_a","speaker_a",wav,sceneadapter.OriginalRights,1152,1024,env())
   if err==nil{t.Fatal("unqualified input admitted")}
  })
 }
 s:=fixture(wav)
 bad:=append([]byte{},wav...);bad[80]^=1
 if _,_,_,err:=Plan(s,"emitter_a","speaker_a",bad,sceneadapter.OriginalRights,1152,1024,env());err==nil{
  t.Fatal("tampered WAV accepted")
 }
 if _,_,_,err:=Plan(s,"emitter_a","speaker_a",wav,"PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL",1152,1024,env());err==nil{
  t.Fatal("classification assertion substituted for first-party rights")
 }
 if _,_,_,err:=Plan(s,"emitter_a","speaker_a",wav,sceneadapter.OriginalRights,4700,1024,env());err==nil{
  t.Fatal("out-of-bounds source extraction admitted")
 }
}
