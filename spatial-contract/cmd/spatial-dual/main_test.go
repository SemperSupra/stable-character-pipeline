package main

import (
 "os"
 "path/filepath"
 "strings"
 "testing"
 "example.invalid/spatial-contract/contract"
)

func admitted(t *testing.T)(contract.Scene,string,[]contract.AssetReceipt){
 t.Helper()
 dir:=filepath.Join(t.TempDir(),"fixture")
 if e:=fixture(dir);e!=nil{t.Fatal(e)}
 s,e:=contract.Load(filepath.Join(dir,"scene.json"));if e!=nil{t.Fatal(e)}
 receipts,e:=contract.AdmitSources(s,dir,true);if e!=nil{t.Fatal(e)}
 return s,dir,receipts
}
func TestActualDualSourceAndMotion(t *testing.T){
 s,_,assets:=admitted(t)
 if len(assets)!=2||assets[0].SHA256==assets[1].SHA256 {t.Fatal("not independent sources")}
 lines,receipt,e:=build(s,assets);if e!=nil{t.Fatal(e)}
 if len(lines)!=47||receipt.Frames!=48000||receipt.LastBlock!=896||len(receipt.Tracks)!=2{t.Fatal("wrong plan",receipt)}
 if !strings.Contains(lines[0],"robot_a")||!strings.Contains(lines[0],"robot_b"){t.Fatal("lost source IDs")}
 a0,e:=contract.PoseAtFrame(s,"robot_a",0);if e!=nil{t.Fatal(e)}
 b0,e:=contract.PoseAtFrame(s,"robot_b",0);if e!=nil{t.Fatal(e)}
 if a0.AzimuthDeg>=0||b0.AzimuthDeg<=0{t.Fatal("initial sources not on opposite sides")}
 ah,e:=contract.PoseAtFrame(s,"robot_a",24000);if e!=nil{t.Fatal(e)}
 bh,e:=contract.PoseAtFrame(s,"robot_b",24000);if e!=nil{t.Fatal(e)}
 if ah.AzimuthDeg<=0||bh.AzimuthDeg>=0{t.Fatal("source trajectories did not cross")}
}
func TestDualRedTeam(t *testing.T){
 cases:=[]struct{name string;change func(*contract.Scene,[]contract.AssetReceipt)}{
  {"missing second",func(s *contract.Scene,_ []contract.AssetReceipt){s.Emitters=s.Emitters[:1]}},
  {"duplicate id",func(s *contract.Scene,_ []contract.AssetReceipt){s.Emitters[1].ID="robot_a"}},
  {"swapped tracks",func(s *contract.Scene,_ []contract.AssetReceipt){s.Emitters[0],s.Emitters[1]=s.Emitters[1],s.Emitters[0]}},
  {"same input file",func(s *contract.Scene,_ []contract.AssetReceipt){s.Emitters[1].AudioAsset=s.Emitters[0].AudioAsset}},
  {"changed hash",func(s *contract.Scene,_ []contract.AssetReceipt){s.Emitters[1].AssetSHA256=s.Emitters[0].AssetSHA256}},
  {"cardioid",func(s *contract.Scene,_ []contract.AssetReceipt){s.Emitters[0].Directivity="cardioid"}},
  {"positive gain",func(s *contract.Scene,_ []contract.AssetReceipt){s.Emitters[1].GainDB=5}},
  {"unsupported spread",func(s *contract.Scene,_ []contract.AssetReceipt){s.Emitters[0].SpreadDeg=30}},
  {"private class",func(s *contract.Scene,_ []contract.AssetReceipt){s.Classification=contract.Private}},
  {"second receipt swapped",func(_ *contract.Scene,r []contract.AssetReceipt){r[0],r[1]=r[1],r[0]}},
  {"wrong target",func(s *contract.Scene,_ []contract.AssetReceipt){for i:=range s.Outputs {if s.Outputs[i].Profile=="surround_5_1"{s.Outputs[i].Profile="binaural"}}}},
 }
 for _,tt:=range cases{t.Run(tt.name,func(t *testing.T){
  s,_,r:=admitted(t)
  tt.change(&s,r)
  if _,_,e:=build(s,r);e==nil{t.Fatal("invalid source plan admitted")}
 })}
}
func TestDualNoOverwriteAndTamperedWave(t *testing.T){
 s,dir,_:=admitted(t)
 out:=filepath.Join(t.TempDir(),"plan.tsv")
 if e:=plan(filepath.Join(dir,"scene.json"),dir,out);e!=nil{t.Fatal(e)}
 before,e:=os.ReadFile(out);if e!=nil{t.Fatal(e)}
 if e=plan(filepath.Join(dir,"scene.json"),dir,out);e==nil{t.Fatal("clobbered existing plan")}
 after,e:=os.ReadFile(out);if e!=nil||string(before)!=string(after){t.Fatal("changed existing plan")}
 if e=os.WriteFile(filepath.Join(dir,"robot_b.wav"),[]byte("bad"),0600);e!=nil{t.Fatal(e)}
 if _,e=contract.AdmitSources(s,dir,true);e==nil{t.Fatal("tampered independent source admitted")}
}
