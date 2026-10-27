package contract

import (
 "encoding/json"
 "os"
 "path/filepath"
 "testing"
)

func TestSourceAndOutputProfiles(t *testing.T){
 s:=SyntheticFixture()
 h,e:=s.Admission(true);if e!=nil{t.Fatal(e)}
 if len(h)!=64 || len(s.Outputs)!=7{t.Fatal("invalid fixture receipt")}
 want:=[]int{2,2,2,6,8,10,12}
 for i,v:=range s.Outputs{if len(v.Channels)!=want[i]{t.Errorf("%s: %d",v.Profile,len(v.Channels))}}
}
func TestNegativeSpatialAdmissions(t *testing.T){
 cases:=[]struct{name string; update func(*Scene)}{
  {"unknown schema",func(s *Scene){s.Schema="audio.v0"}},
  {"ambiguous coordinates",func(s *Scene){s.WorldFrame="xright_yup_zforward"}},
  {"private source",func(s *Scene){s.Classification=Private}},
  {"unrecognized category",func(s *Scene){s.Emitters[0].Category="classified"}},
  {"source escape",func(s *Scene){s.Emitters[0].AudioAsset="../secret.wav"}},
  {"negative gain",func(s *Scene){s.Emitters[0].GainDB=-81}},
  {"too many degrees",func(s *Scene){s.Emitters[0].SpreadDeg=181}},
  {"missing first keyframe",func(s *Scene){s.Emitters[0].Motion=s.Emitters[0].Motion[1:]}},
  {"duplicate time",func(s *Scene){s.Emitters[0].Motion[1].TimeMS=0}},
  {"wrong channel ordering",func(s *Scene){s.Outputs[3].Channels[0]="FR"}},
  {"wrong LFE policy",func(s *Scene){s.Outputs[1].LFEPolicy="discrete"}},
  {"missing HRTF custody",func(s *Scene){s.Outputs[2].HRTF=""}},
  {"double HRTF",func(s *Scene){s.Outputs[0].HRTF="builtin_mit_test"}},
  {"duplicate emitter id",func(s *Scene){s.Emitters[0].ID=s.ListenerID}},
 }
 for _,tt:=range cases{t.Run(tt.name,func(t *testing.T){
  s:=SyntheticFixture();tt.update(&s)
  if _,e:=s.Admission(true);e==nil{t.Fatal("unsafe fixture passed") }
 })}
}
func TestPrivateLocalGate(t *testing.T){
 s:=SyntheticFixture();s.Classification=Private
 if _,e:=s.Admission(true);e==nil{t.Fatal("private admitted on public worker")}
 if _,e:=s.Admission(false);e!=nil{t.Fatal(e)}
}
func TestStrictLoad(t *testing.T){
 s:=SyntheticFixture()
 b,e:=json.Marshal(s);if e!=nil{t.Fatal(e)}
 path:=filepath.Join(t.TempDir(),"scene.json")
 if e=os.WriteFile(path,b,0600);e!=nil{t.Fatal(e)}
 parsed,e:=Load(path);if e!=nil{t.Fatal(e)}
 if parsed.ID!=s.ID{t.Fatal("wrong ID")}
 if e=os.WriteFile(path,append(b,[]byte("{}")...),0600);e!=nil{t.Fatal(e)}
 if _,e=Load(path);e==nil{t.Fatal("trailing JSON accepted")}
}
