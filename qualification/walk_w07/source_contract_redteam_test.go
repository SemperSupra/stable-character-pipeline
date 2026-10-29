package main

import (
 "encoding/json"
 "os"
 "testing"
)
func corruptedFixture(t *testing.T,change func(map[string]any)) Source{
 t.Helper()
 p:=os.Getenv("W07_TEST_SOURCE")
 if p==""{t.Fatal("missing W07_TEST_SOURCE")}
 raw,e:=os.ReadFile(p);if e!=nil{t.Fatal(e)}
 var packet map[string]any
 if e=json.Unmarshal(raw,&packet);e!=nil{t.Fatal(e)}
 change(packet)
 b,e:=json.Marshal(packet);if e!=nil{t.Fatal(e)}
 var source Source
 if e=json.Unmarshal(b,&source);e!=nil{t.Fatal(e)}
 return source
}
func requireDenied(t *testing.T,mutation func(map[string]any)){
 t.Helper()
 s:=corruptedFixture(t,mutation)
 _,e:=Retarget(s,"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","different-proportions")
 if e==nil{t.Fatalf("W12 ADMISSION FIRST FAILURE: corrupted canonical source passed source-only Go retarget")}
}
func TestRejectForgedTimeS(t *testing.T){
 requireDenied(t,func(p map[string]any){f:=p["frames"].([]any)[3].(map[string]any);f["time_s"]=123.0})
}
func TestRejectMissingTimeS(t *testing.T){
 requireDenied(t,func(p map[string]any){f:=p["frames"].([]any)[3].(map[string]any);delete(f,"time_s")})
}
func TestRejectAlteredGeometrySpace(t *testing.T){
 requireDenied(t,func(p map[string]any){p["geometry_space"]="TRUE_METRIC_3D_UNVERIFIED"})
}
func TestRejectForgedCharacterSourceClassification(t *testing.T){
 requireDenied(t,func(p map[string]any){p["classification"]="THIRD_PARTY_PRIVATE"})
}
func TestRejectAlteredTransferIntent(t *testing.T){
 requireDenied(t,func(p map[string]any){p["transfer_intent"]="SILENT_PRIVATE_ASSET_DISPATCH"})
}
func TestRejectMissingCanonicalJointWithExtraDecoy(t *testing.T){
 requireDenied(t,func(p map[string]any){
  f:=p["frames"].([]any)[8].(map[string]any)
  actors:=f["actors"].(map[string]any)
  a:=actors[IDs[0]].(map[string]any)
  j:=a["joints"].(map[string]any)
  delete(j,"head")
  j["decoy_joint"]=[]any{0.,0.}
 })
}
func TestRejectWrongContactKeyWithSameLength(t *testing.T){
 requireDenied(t,func(p map[string]any){
  f:=p["frames"].([]any)[2].(map[string]any)
  a:=f["actors"].(map[string]any)[IDs[0]].(map[string]any)
  contact:=a["contact"].(map[string]any)
  delete(contact,"right")
  contact["deception"]=true
 })
}
