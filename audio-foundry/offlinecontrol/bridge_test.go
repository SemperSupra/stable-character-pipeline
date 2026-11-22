package offlinecontrol

import (
 "bytes"
 "encoding/binary"
 "errors"
 "math"
 "os"
 "os/exec"
 "path/filepath"
 "testing"

 "example.invalid/audio-foundry-fixture/scene"
)
func syntheticStereoWAV(t *testing.T, filename string){
 t.Helper()
 const sr=48000
 const frames=sr
 var raw bytes.Buffer
 raw.WriteString("RIFF")
 _=binary.Write(&raw,binary.LittleEndian,uint32(36+frames*4))
 raw.WriteString("WAVEfmt ")
 _=binary.Write(&raw,binary.LittleEndian,uint32(16))
 _=binary.Write(&raw,binary.LittleEndian,uint16(1))
 _=binary.Write(&raw,binary.LittleEndian,uint16(2))
 _=binary.Write(&raw,binary.LittleEndian,uint32(sr))
 _=binary.Write(&raw,binary.LittleEndian,uint32(sr*4))
 _=binary.Write(&raw,binary.LittleEndian,uint16(4))
 _=binary.Write(&raw,binary.LittleEndian,uint16(16))
 raw.WriteString("data")
 _=binary.Write(&raw,binary.LittleEndian,uint32(frames*4))
 for n:=0;n<frames;n++{
  value:=int16(math.Round(0.08*32767*math.Sin(2*math.Pi*410*float64(n)/sr)))
  _=binary.Write(&raw,binary.LittleEndian,value)
  _=binary.Write(&raw,binary.LittleEndian,value)
 }
 if err:=os.WriteFile(filename,raw.Bytes(),0600);err!=nil{t.Fatal(err)}
}
func fixture(t *testing.T)(scene.Manifest,string,string){
 t.Helper()
 root:=t.TempDir()
 input:=filepath.Join(root,"source.wav")
 syntheticStereoWAV(t,input)
 digest,_,err:=scene.Hash(input);if err!=nil{t.Fatal(err)}
 m:=scene.Manifest{Schema:scene.Schema,ID:"synthetic_offline_probe",Classification:scene.Public,
  DurationMS:1000,SampleRateHz:48000,Channels:2,
  Tracks:[]scene.Track{{ID:"tone",Category:"foley",Asset:"source.wav",SHA256:digest,
   StartMS:0,DurationMS:1000}}}
 output:=filepath.Join(t.TempDir(),"mix.wav")
 return m,root,output
}
func TestOfflineSceneRealRenderAndRetryRefusal(t *testing.T){
 if _,err:=exec.LookPath("ffmpeg");err!=nil{t.Skip("FFmpeg absent")}
 if _,err:=exec.LookPath("ffprobe");err!=nil{t.Skip("ffprobe absent")}
 m,root,out:=fixture(t)
 p,err:=Prepare(m,root,out);if err!=nil{t.Fatal(err)}
 if len(p.Fingerprint())!=64{t.Fatal("missing source fingerprint")}
 receipt,err:=p.Execute();if err!=nil{t.Fatal(err)}
 if receipt.OutputSHA256==""||receipt.OutputBytes<100000{t.Fatalf("not a real WAV: %+v",receipt)}
 ok,err:=VerifyOutput(out,receipt.OutputSHA256);if err!=nil||!ok{t.Fatalf("output unverifiable: %v",err)}
 if _,err:=p.Execute();!errors.Is(err,ErrOutputExists){t.Fatalf("repeat effect was not refused: %v",err)}
 ok,err=VerifyOutput(out,receipt.OutputSHA256);if err!=nil||!ok{t.Fatal("retry changed verified output")}
 // This is safely non-overwriting, not a durable exactly-once operation receipt.
}
func TestInputMutatedBetweenPlanAndApply(t *testing.T){
 m,root,out:=fixture(t)
 p,err:=Prepare(m,root,out);if err!=nil{t.Fatal(err)}
 input:=filepath.Join(root,"source.wav")
 if err:=os.WriteFile(input,[]byte("changed public fixture"),0600);err!=nil{t.Fatal(err)}
 if _,err:=p.Execute();err==nil{t.Fatal("changed asset rendered")}
 if _,err:=os.Lstat(out);!os.IsNotExist(err){t.Fatal("failure wrote output")}
}
func TestUnsafeAndPrivatePlansFailClosed(t *testing.T){
 m,root,out:=fixture(t)
 m.Classification=scene.Private
 if _,err:=Prepare(m,root,out);err==nil{t.Fatal("private final voice/content admitted")}
 m.Classification=scene.Public
 if _,err:=Prepare(m,root,filepath.Join(root,"..","bad.wav"));err==nil{t.Fatal("unclean output path admitted")}
 if _,err:=Prepare(m,root,"relative.wav");err==nil{t.Fatal("relative output admitted")}
 victim:=filepath.Join(root,"source.wav")
 if err:=os.Symlink(victim,out);err!=nil{t.Skip(err)}
 if _,err:=Prepare(m,root,out);!errors.Is(err,ErrOutputExists){t.Fatalf("symlink output admitted: %v",err)}
}
