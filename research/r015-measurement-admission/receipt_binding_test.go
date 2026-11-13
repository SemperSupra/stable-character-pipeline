package r015gate

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"
)

func digest(b []byte) string {
 h:=sha256.Sum256(b);return hex.EncodeToString(h[:])
}
func contains(a []string,q string) bool{
 for _,s:=range a {if s==q{return true}}
 return false
}
func validFixture(t *testing.T)(Evidence,BoundProof){
 t.Helper()
 dir:=t.TempDir()
 geometry:=[]byte("synthetic geometrical FICTION, not a real 3D body: repeatable test bytes")
 g:=filepath.Join(dir,"geometry.bytes")
 if err:=os.WriteFile(g,geometry,0600);err!=nil{t.Fatal(err)}
 h:=digest(geometry)
 m:=Measurement{Name:"stature",Value:1.83,Unit:"m",Method:"fake_test_caliper",SourceSHA:h,LandmarkProvenance:"synthetic endpoints"}
 e:=Evidence{AdultAsserted:true,RightsKnown:true,EvaluatedMesh:true,
  NativeReopened:true,IndependentScaleCalibrated:true,OutOfDistributionKnown:true,
  HeldoutIndependent:true,Measurements:[]Measurement{m}}
 payload,_:=json.Marshal(MeasurementReceipt{
  Schema:"r015.measurement.claims.source_bound.v1",GeometrySHA256:h,
  Measurements:e.Measurements,ClaimedScaleMethod:"self-asserted-test-fixture",
  ClaimedIssuer:"self-asserted-not-a-trusted-verifier"})
 p:=filepath.Join(dir,"measures.json")
 if err:=os.WriteFile(p,payload,0600);err!=nil{t.Fatal(err)}
 return e,BoundProof{GeometryPath:g,GeometrySHA256:h,MeasurementReceiptPath:p,
  MeasurementReceiptSHA256:digest(payload)}
}
func TestAdversarialByteBindings(t *testing.T){
 t.Run("CallerSelfAssertionOldPrototypePassButBoundGateAbstains",func(t *testing.T){
  e,p:=validFixture(t)
  if x:=Check(e);x.Status!=Pass{t.Fatalf("old structural positive changed: %#v",x)}
  x:=CheckBound(e,p)
  if x.Status!=Unknown||!contains(x.Reasons,"byte_binding_verified"){
   t.Fatalf("self-asserted evidence must abstain even after byte-integrity proof: %#v",x)
  }
 })
 t.Run("TamperedGeometryReject",func(t *testing.T){
  e,p:=validFixture(t)
  if err:=os.WriteFile(p.GeometryPath,[]byte("tampered but name unchanged"),0600);err!=nil{t.Fatal(err)}
  if x:=CheckBound(e,p);x.Status!=Reject{t.Fatalf("%#v",x)}
 })
 t.Run("SpoofedHashWithAllFlagsTrueReject",func(t *testing.T){
  e,p:=validFixture(t);e.Measurements[0].SourceSHA="not-a-hash"
  if x:=CheckBound(e,p);x.Status!=Reject{t.Fatalf("%#v",x)}
 })
 t.Run("FakeButValidDigestUnboundReject",func(t *testing.T){
  e,p:=validFixture(t);e.Measurements[0].SourceSHA=strings.Repeat("f",64)
  if x:=CheckBound(e,p);x.Status!=Reject{t.Fatalf("%#v",x)}
 })
 t.Run("CorruptedReceiptDigestReject",func(t *testing.T){
  e,p:=validFixture(t)
  f,err:=os.OpenFile(p.MeasurementReceiptPath,os.O_APPEND|os.O_WRONLY,0600);if err!=nil{t.Fatal(err)}
  if _,err:=f.WriteString(" ");err!=nil{t.Fatal(err)};f.Close()
  if x:=CheckBound(e,p);x.Status!=Reject{t.Fatalf("%#v",x)}
 })
 t.Run("MeasurementValueSpoofReject",func(t *testing.T){
  e,p:=validFixture(t);e.Measurements[0].Value=2.35
  if x:=CheckBound(e,p);x.Status!=Reject{t.Fatalf("%#v",x)}
 })
 t.Run("LandmarkSpoofReject",func(t *testing.T){
  e,p:=validFixture(t);e.Measurements[0].LandmarkProvenance="fabricated-other-landmark"
  if x:=CheckBound(e,p);x.Status!=Reject{t.Fatalf("%#v",x)}
 })
 t.Run("ReceiptSwappedGeometryReject",func(t *testing.T){
  e,p:=validFixture(t);p.GeometrySHA256=digest([]byte("different original artifact"))
  if x:=CheckBound(e,p);x.Status!=Reject{t.Fatalf("%#v",x)}
 })
 t.Run("MissingFileReject",func(t *testing.T){
  e,p:=validFixture(t);os.Remove(p.GeometryPath)
  if x:=CheckBound(e,p);x.Status!=Reject{t.Fatalf("%#v",x)}
 })
 t.Run("UnknownReceiptSchemaReject",func(t *testing.T){
  e,p:=validFixture(t)
  raw,_:=os.ReadFile(p.MeasurementReceiptPath)
  raw=bytes.ReplaceAll(raw,[]byte("r015.measurement.claims.source_bound.v1"),
                           []byte("other.measurement.claims.source_bound.v1"))
  if err:=os.WriteFile(p.MeasurementReceiptPath,raw,0600);err!=nil{t.Fatal(err)}
  p.MeasurementReceiptSHA256=digest(raw)
  if x:=CheckBound(e,p);x.Status!=Reject{t.Fatalf("%#v",x)}
 })
 t.Run("RightsFalseStillAbstains",func(t *testing.T){
  e,p:=validFixture(t);e.RightsKnown=false
  if x:=CheckBound(e,p);x.Status!=Unknown{t.Fatalf("%#v",x)}
 })
 t.Run("NoAdultAssertionReject",func(t *testing.T){
  e,p:=validFixture(t);e.AdultAsserted=false
  if x:=CheckBound(e,p);x.Status!=Reject{t.Fatalf("%#v",x)}
 })
}
