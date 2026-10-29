package cuebridge

import (
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "math"
 "testing"
 "example.invalid/spatial-contract/avsync"
 "example.invalid/spatial-contract/contract"
)
func original(frames int)[]byte {
 b:=make([]byte,44+frames*2)
 copy(b[:4],"RIFF");binary.LittleEndian.PutUint32(b[4:],uint32(len(b)-8))
 copy(b[8:16],"WAVEfmt ");binary.LittleEndian.PutUint32(b[16:],16)
 binary.LittleEndian.PutUint16(b[20:],1);binary.LittleEndian.PutUint16(b[22:],1)
 binary.LittleEndian.PutUint32(b[24:],48000);binary.LittleEndian.PutUint32(b[28:],96000)
 binary.LittleEndian.PutUint16(b[32:],2);binary.LittleEndian.PutUint16(b[34:],16)
 copy(b[36:40],"data");binary.LittleEndian.PutUint32(b[40:],uint32(frames*2))
 for i:=0;i<frames;i++{binary.LittleEndian.PutUint16(b[44+2*i:],uint16(int16(math.Round(.1*32767*math.Sin(2*math.Pi*410*float64(i)/48000)))))}
 return b
}
func synthetic(clip bool)(contract.Scene,map[string][]byte,[]Annotation){
 w:=original(9600);hash:=sha256.Sum256(w)
 e:=contract.Emitter{ID:"emitter_a",Category:"foley",AudioAsset:"original.wav",
  AssetSHA256:hex.EncodeToString(hash[:]),Directivity:"omni",
  Motion:[]contract.Key{{TimeMS:0,Position:contract.Vec3{X:1,Y:0,Z:0}}},
  SourceStartFrame:480,SourceStopFrame:9000}
 if clip{e.SourceTransport="clip_relative";e.SourceOffsetFrame=96}
 s:=contract.Scene{Schema:contract.Schema,ID:"scene_test",Classification:contract.Public,
  WorldFrame:contract.WorldFrame,SampleRateHz:48000,DurationMS:200,
  ListenerID:"listener_b",Listener:[]contract.Key{{TimeMS:0,Position:contract.Vec3{X:0,Y:0,Z:0}}},
  Emitters:[]contract.Emitter{e},
  Outputs:[]contract.Output{{ID:"stereo_a",Profile:"stereo",Channels:[]string{"L","R"},LFEPolicy:"none"}}}
 anns:=[]Annotation{
  {ID:"cue_foot",EmitterID:"emitter_a",Kind:avsync.FootContact,Label:"heel",AtSample:960},
  {ID:"cue_dialogue",EmitterID:"emitter_a",Kind:avsync.DialogueStart,Label:"utterance",AtSample:2400},
  {ID:"cue_phoneme",EmitterID:"emitter_a",Kind:avsync.PhonemeBoundary,Label:"p",AtSample:4800},
  {ID:"cue_gesture",EmitterID:"emitter_a",Kind:avsync.GestureBeat,Label:"accent",AtSample:7200},
 }
 return s,map[string][]byte{"emitter_a":w},anns
}
func TestTransportBatch24Controls(t *testing.T){
 for _,rate:=range []avsync.Rate{{Num:24,Den:1},{Num:30,Den:1},{Num:30000,Den:1001}}{
  for _,clip:=range []bool{false,true}{
   s,src,anns:=synthetic(clip)
   rec,err:=Build(s,src,anns,rate,Rights)
   if err!=nil{t.Fatalf("%+v clip%v: %v",rate,clip,err)}
   if len(rec.Cues)!=4||len(rec.CanonicalSceneSHA256)!=64{t.Fatal("lost custody")}
   for _,cue:=range rec.Cues{
    want:=cue.SceneSample
    if clip{want=cue.SceneSample-480+96}
    if cue.SourceSample!=want{t.Fatalf("offset %d expected %d",cue.SourceSample,want)}
    vf,err:=avsync.FrameContainingSample(cue.SceneSample,rate)
    if err!=nil||cue.VideoFrame!=vf{t.Fatal("video frame mismatch")}
   }
  }
 }
}
func TestRejectAdversarialCanonicalAssets(t *testing.T){
 run:=func(mod func(*contract.Scene,map[string][]byte,*[]Annotation),want bool){
  s,files,anns:=synthetic(false);mod(&s,files,&anns)
  _,err:=Build(s,files,anns,avsync.Rate{Num:30,Den:1},Rights)
  if (err==nil)!=want{t.Fatalf("wrong admission result %v",err)}
 }
 negs:=[]func(*contract.Scene,map[string][]byte,*[]Annotation){
  func(s *contract.Scene,m map[string][]byte,a *[]Annotation){s.Classification=contract.Private},
  func(s *contract.Scene,m map[string][]byte,a *[]Annotation){x:=append([]byte{},m["emitter_a"]...);x[48]^=1;m["emitter_a"]=x},
  func(s *contract.Scene,m map[string][]byte,a *[]Annotation){delete(m,"emitter_a")},
  func(s *contract.Scene,m map[string][]byte,a *[]Annotation){(*a)[0].AtSample=479},
  func(s *contract.Scene,m map[string][]byte,a *[]Annotation){(*a)[0].AtSample=9000},
  func(s *contract.Scene,m map[string][]byte,a *[]Annotation){(*a)[0].AtSample=-1},
  func(s *contract.Scene,m map[string][]byte,a *[]Annotation){(*a)[1].ID=(*a)[0].ID},
  func(s *contract.Scene,m map[string][]byte,a *[]Annotation){(*a)[2].Kind=avsync.CameraCut},
  func(s *contract.Scene,m map[string][]byte,a *[]Annotation){(*a)[2].Label="not allowed"},
  func(s *contract.Scene,m map[string][]byte,a *[]Annotation){(*a)[2].EmitterID="other"},
  func(s *contract.Scene,m map[string][]byte,a *[]Annotation){s.Emitters[0].SourceTransport="clip_relative";s.Emitters[0].SourceOffsetFrame=1500;s.Emitters[0].SourceStopFrame=9000},
  func(s *contract.Scene,m map[string][]byte,a *[]Annotation){s.Listener[0].Position.X=math.NaN()},
  func(s *contract.Scene,m map[string][]byte,a *[]Annotation){s.Emitters[0].Motion[0].TimeMS=10},
 }
 for _,mut:=range negs{run(mut,false)}
 run(func(s *contract.Scene,m map[string][]byte,a *[]Annotation){},true)
}
