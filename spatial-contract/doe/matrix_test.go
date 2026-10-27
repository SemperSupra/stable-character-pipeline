package doe

import (
 "math"
 "testing"
 "example.invalid/spatial-contract/contract"
)
func TestCompleteGeometryAndNoFalseEvidence(t *testing.T){
 m,e:=Generate();if e!=nil{t.Fatal(e)}
 if m.Schema!=Schema||m.TimebaseHz!=48000||len(m.Cases)!=42||m.Classification!=contract.Public {t.Fatal("DoE missing authority")}
 ids:=map[string]bool{}
 for _,v:=range m.Cases{
  if ids[v.ID]{t.Fatal("duplicate source configuration")};ids[v.ID]=true
  if v.EBUResult!="NOT_MEASURED"||v.VideoLANResult!="NOT_MEASURED"{t.Fatal("false independent source equivalence admission")}
  if len(v.Layouts)!=2||v.Layouts[0]!="surround_5_1"||v.Layouts[1]!="surround_7_1"{t.Fatal("unsupported layout experiment")}
  if math.Abs(v.Recovered.DistanceM-10)>1e-8||math.Abs(v.Recovered.ElevationDeg-v.ElevationDeg)>1e-8{t.Fatal("dimension mismatch")}
  // Translating both source and listener must leave angular geometry invariant.
  scene:=contract.SyntheticFixture()
  shift:=contract.Vec3{X:123,Y:-321,Z:14}
  scene.Listener=[]contract.Key{{TimeMS:0,Position:contract.Vec3{X:v.ListenerPositionENU.X+shift.X,Y:v.ListenerPositionENU.Y+shift.Y,Z:v.ListenerPositionENU.Z+shift.Z},YawDeg:v.ListenerYawDeg}}
  scene.Emitters[0].Motion=[]contract.Key{{TimeMS:0,Position:contract.Vec3{X:v.SourcePositionENU.X+shift.X,Y:v.SourcePositionENU.Y+shift.Y,Z:v.SourcePositionENU.Z+shift.Z}}}
  pose,e:=contract.PoseAtFrame(scene,scene.Emitters[0].ID,0);if e!=nil{t.Fatal(e)}
  if math.Abs(normalize(pose.AzimuthDeg-v.RelativeAzimuthDeg))>1e-8||math.Abs(pose.ElevationDeg-v.ElevationDeg)>1e-8{t.Fatalf("origin-sensitive test %s %+v",v.ID,pose)}
 }
}
func TestCoverage(t *testing.T){
 m,e:=Generate();if e!=nil{t.Fatal(e)}
 got:=map[string]int{};signs:=map[string]bool{}
 for _,v:=range m.Cases{
  k:=v.ID[:7];got[k]++
  if v.RelativeAzimuthDeg<0{signs["negative"]=true}
  if v.RelativeAzimuthDeg>0{signs["positive"]=true}
  if v.RelativeAzimuthDeg==0{signs["front"]=true}
  if v.RelativeAzimuthDeg==-180{signs["rear"]=true}
  if v.ElevationDeg==30{signs["height"]=true}
 }
 if len(got)!=3||len(signs)!=5{t.Fatal("missing listener orientations or source classes",got,signs)}
 for _,n:=range got{if n!=14{t.Fatal("unbalanced DoE")}}
}
