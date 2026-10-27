package contract

import (
 "encoding/binary"
 "errors"
 "math"
 "os"
 "path/filepath"
 "testing"
)

func realScene(t *testing.T)(Scene,string){
 t.Helper()
 root:=t.TempDir()
 hash,e:=WriteOriginalSine(filepath.Join(root,"synthetic.wav"),1000)
 if e!=nil{t.Fatal(e)}
 s:=SyntheticFixture();s.Emitters[0].AssetSHA256=hash
 return s,root
}
func TestRealWAVAdmission(t *testing.T){
 s,root:=realScene(t)
 r,e:=AdmitSources(s,root,true);if e!=nil{t.Fatal(e)}
 if len(r)!=1 || r[0].Frames!=48000||r[0].Bytes!=96044||r[0].SHA256!=s.Emitters[0].AssetSHA256{t.Fatalf("wrong actual PCM admission %+v",r)}
 // Re-admission is deterministic; no source mutation or output overwrite.
 r2,e:=AdmitSources(s,root,true);if e!=nil || r2[0].SHA256!=r[0].SHA256{t.Fatal("non-idempotent admission",e)}
}
func TestRealWAVFailClosed(t *testing.T){
 cases:=[]struct{name string; act func(*Scene,string)error}{
  {"fixture placeholder",func(s *Scene,_ string)error{s.Emitters[0].AssetSHA256=SyntheticFixture().Emitters[0].AssetSHA256;return nil}},
  {"wrong hash",func(s *Scene,_ string)error{s.Emitters[0].AssetSHA256="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";return nil}},
  {"private class",func(s *Scene,_ string)error{s.Classification=Private;return nil}},
  {"missing",func(_ *Scene,root string)error{return os.Remove(filepath.Join(root,"synthetic.wav"))}},
  {"file symlink",func(_ *Scene,root string)error{
   src:=filepath.Join(root,"synthetic.wav");renamed:=filepath.Join(root,"copy.wav")
   if e:=os.Rename(src,renamed);e!=nil{return e}
   return os.Symlink(renamed,src)
  }},
  {"truncated",func(_ *Scene,root string)error{return os.Truncate(filepath.Join(root,"synthetic.wav"),96042)}},
  {"modified PCM",func(_ *Scene,root string)error{
   p:=filepath.Join(root,"synthetic.wav");f,e:=os.OpenFile(p,os.O_WRONLY,0);if e!=nil{return e};defer f.Close()
   _,e=f.WriteAt([]byte{10},44);return e
  }},
  {"wrong rate",func(_ *Scene,root string)error{
   p:=filepath.Join(root,"synthetic.wav");f,e:=os.OpenFile(p,os.O_WRONLY,0);if e!=nil{return e};defer f.Close()
   b:=make([]byte,4);binary.LittleEndian.PutUint32(b,44100);_,e=f.WriteAt(b,24);return e
  }},
  {"wrong channels",func(_ *Scene,root string)error{
   p:=filepath.Join(root,"synthetic.wav");f,e:=os.OpenFile(p,os.O_WRONLY,0);if e!=nil{return e};defer f.Close()
   b:=make([]byte,2);binary.LittleEndian.PutUint16(b,2);_,e=f.WriteAt(b,22);return e
  }},
  {"wrong scene duration",func(s *Scene,_ string)error{s.DurationMS=1200;return nil}},
  {"malicious path",func(s *Scene,_ string)error{s.Emitters[0].AudioAsset="../synthetic.wav";return nil}},
  {"other output HRTF",func(s *Scene,_ string)error{s.Outputs[0].HRTF="other";return nil}},
  {"root symlink",func(_ *Scene,root string)error{return errors.New("separate test")}},
 }
 for _,tt:=range cases{
  if tt.name=="root symlink"{continue}
  t.Run(tt.name,func(t *testing.T){
   s,root:=realScene(t);if e:=tt.act(&s,root);e!=nil{t.Fatal(e)}
   if _,e:=AdmitSources(s,root,true);e==nil{t.Fatal("unsafe WAV/source admitted")}
  })
 }
}
func TestSymlinkRootAndNoOverwrite(t *testing.T){
 s,root:=realScene(t)
 link:=filepath.Join(t.TempDir(),"link")
 if e:=os.Symlink(root,link);e!=nil{t.Fatal(e)}
 if _,e:=AdmitSources(s,link,true);e==nil{t.Fatal("symlink root admitted")}
 if _,e:=WriteOriginalSine(filepath.Join(root,"synthetic.wav"),1000);e==nil{t.Fatal("overwrote input")}
 if _,e:=WriteOriginalSine(filepath.Join(root,"new.wav"),700000);e==nil{t.Fatal("unbounded WAV written")}
}
func TestENUCardinalsAndYaw(t *testing.T){
 cases:=[]struct{name string; pos Vec3; yaw float64; az,el,dist float64}{
  {"north",Vec3{0,10,0},0,0,0,10},
  {"east",Vec3{10,0,0},0,90,0,10},
  {"west",Vec3{-10,0,0},0,-90,0,10},
  {"south",Vec3{0,-10,0},0,-180,0,10},
  {"up",Vec3{0,0,8},0,0,90,8},
  {"east with yaw",Vec3{10,0,0},90,0,0,10},
  {"north with yaw",Vec3{0,10,0},90,-90,0,10},
  {"left after half-turn",Vec3{10,0,0},180,-90,0,10},
 }
 for _,tt:=range cases{t.Run(tt.name,func(t *testing.T){
  s:=SyntheticFixture();s.Listener[0].YawDeg=tt.yaw
  s.Emitters[0].Motion=[]Key{{TimeMS:0,Position:tt.pos}}
  got,e:=PoseAtFrame(s,s.Emitters[0].ID,0);if e!=nil{t.Fatal(e)}
  if math.Abs(got.AzimuthDeg-tt.az)>1e-8||math.Abs(got.ElevationDeg-tt.el)>1e-8||math.Abs(got.DistanceM-tt.dist)>1e-8{t.Fatalf("pose mismatch: %+v",got)}
 })}
}
func TestMovingAndSampleAccurate(t *testing.T){
 s:=SyntheticFixture()
 s.Emitters[0].Motion=[]Key{{TimeMS:0,Position:Vec3{-10,10,0}},{TimeMS:500,Position:Vec3{10,10,0}}}
 for _,item:=range []struct{frame int;x,az float64}{
  {0,-10,-45},{12000,-5,-26.56505117707799},{24000,10,45},{47999,10,45},
 } {
  got,e:=PoseAtFrame(s,s.Emitters[0].ID,item.frame);if e!=nil{t.Fatal(e)}
  if math.Abs(got.Relative.X-item.x)>1e-7||math.Abs(got.AzimuthDeg-item.az)>1e-7{t.Fatalf("frame %d pose %+v expected x %.6f az %.6f",item.frame,got,item.x,item.az)}
 }
 // Listener 179 -> -179 interpolates through 180 degrees, not back through zero.
 s.Listener=[]Key{{TimeMS:0,Position:Vec3{},YawDeg:179},{TimeMS:500,Position:Vec3{},YawDeg:-179}}
 p,e:=PoseAtFrame(s,s.Emitters[0].ID,12000);if e!=nil{t.Fatal(e)}
 if math.Abs(p.ListenerYawDeg-(-180))>1.00001{t.Fatal("yaw shortest arc failed",p.ListenerYawDeg)}
}
func TestGeometryNegativeCases(t *testing.T){
 s:=SyntheticFixture()
 if _,e:=PoseAtFrame(s,"not-there",0);e==nil{t.Fatal("unknown emitter")}
 if _,e:=PoseAtFrame(s,s.Emitters[0].ID,48000);e==nil{t.Fatal("out-of-bounds frame")}
 if _,e:=PoseAtFrame(s,s.Emitters[0].ID,-1);e==nil{t.Fatal("negative frame")}
 s.Emitters[0].Motion=[]Key{{TimeMS:0,Position:Vec3{0,0,0}}}
 if _,e:=PoseAtFrame(s,s.Emitters[0].ID,0);e==nil{t.Fatal("undefined coincident emitter accepted")}
 s.Emitters[0].Motion=[]Key{{TimeMS:0,Position:Vec3{0,1,0}}}
 s.Emitters[0].SpreadDeg=20
 if _,e:=PoseAtFrame(s,s.Emitters[0].ID,0);e==nil{t.Fatal("unsupported spread accepted")}
 s.Emitters[0].SpreadDeg=0
 s.Emitters[0].Motion[0].Position.X=math.NaN()
 if _,e:=PoseAtFrame(s,s.Emitters[0].ID,0);e==nil{t.Fatal("nonfinite coordinate accepted")}
}
