package scene
import (
 "os"
 "path/filepath"
 "testing"
)
func fixture(t *testing.T)(Manifest,string){
 t.Helper()
 d:=t.TempDir()
 if e:=os.WriteFile(filepath.Join(d,"clip.wav"),[]byte("synthetic fixture"),0600);e!=nil{t.Fatal(e)}
 h,_,e:=Hash(filepath.Join(d,"clip.wav"));if e!=nil{t.Fatal(e)}
 m:=Manifest{Schema:Schema,ID:"test",Classification:Public,DurationMS:12000,SampleRateHz:48000,Channels:2,
  Tracks:[]Track{{ID:"clip",Category:"foley",Asset:"clip.wav",SHA256:h,StartMS:0,DurationMS:12000}}}
 return m,d
}
func TestContractAndHash(t *testing.T){
 m,d:=fixture(t)
 if e:=m.Validate();e!=nil{t.Fatal(e)}
 r,e:=m.Plan(d,false);if e!=nil{t.Fatal(e)}
 if len(r.Assets)!=1||r.Assets[0].SHA256!=m.Tracks[0].SHA256{t.Fatal("source receipt mismatch")}
 if e:=os.WriteFile(filepath.Join(d,"clip.wav"),[]byte("tampered"),0600);e!=nil{t.Fatal(e)}
 if _,e:=m.Plan(d,false);e==nil{t.Fatal("tampered source admitted")}
}
func TestNegativeFalsifiers(t *testing.T){
 checks:=[]struct{name string; mutate func(*Manifest)}{
  {"unknown schema",func(m *Manifest){m.Schema="v0"}},
  {"unsafe path",func(m *Manifest){m.Tracks[0].Asset="../clip.wav"}},
  {"absolute path",func(m *Manifest){m.Tracks[0].Asset="/tmp/clip.wav"}},
  {"missing digest",func(m *Manifest){m.Tracks[0].SHA256=""}},
  {"unexpected category",func(m *Manifest){m.Tracks[0].Category="alien_weapon"}},
  {"excessive start",func(m *Manifest){m.Tracks[0].StartMS=1000}},
  {"negative offset",func(m *Manifest){m.Tracks[0].OffsetMS=-1}},
  {"oversized fades",func(m *Manifest){m.Tracks[0].FadeInMS=8000;m.Tracks[0].FadeOutMS=8000}},
  {"invalid channels",func(m *Manifest){m.Channels=7}},
  {"invalid sample rate",func(m *Manifest){m.SampleRateHz=9600}},
  {"duplicate ids",func(m *Manifest){m.Tracks=append(m.Tracks,m.Tracks[0])}},
  {"unknown event track",func(m *Manifest){m.Events=[]Event{{ID:"x",TrackID:"nonexistent",EntityID:"robot",Kind:"speak",TimeMS:2}}}},
 }
 for _,x:=range checks{t.Run(x.name,func(t *testing.T){
  m,_:=fixture(t);x.mutate(&m)
  if e:=m.Validate();e==nil{t.Fatal("negative fixture admitted")}
 })}
}
func TestPrivateGate(t *testing.T){
 m,d:=fixture(t);m.Classification=Private
 if _,e:=m.Plan(d,false);e==nil{t.Fatal("private content entered public plan")}
 if _,e:=m.Plan(d,true);e!=nil{t.Fatal(e)}
}
func TestSymlinkReject(t *testing.T){
 m,d:=fixture(t)
 p:=filepath.Join(d,"clip.wav")
 if e:=os.Remove(p);e!=nil{t.Fatal(e)}
 target:=filepath.Join(t.TempDir(),"other.wav")
 if e:=os.WriteFile(target,[]byte("synthetic fixture"),0600);e!=nil{t.Fatal(e)}
 if e:=os.Symlink(target,p);e!=nil{t.Fatal(e)}
 if _,e:=m.Plan(d,false);e==nil{t.Fatal("symlink admitted")}
}
func TestUnsafePaths(t *testing.T){
 if SafeAsset("sub/../clip.wav") || SafeAsset("C:\\secret.wav") || SafeAsset("/root/secret.wav") {t.Fatal("unsafe paths allowed")}
}
