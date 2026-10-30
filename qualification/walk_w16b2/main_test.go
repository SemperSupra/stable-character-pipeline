package main
import (
 "encoding/json"
 "os"
 "testing"
 "./typed"
)
func fixture(t *testing.T)[]byte{t.Helper();b,e:=os.ReadFile("../walk_w16b/fixtures_w13a_pinned.json");if e!=nil{t.Fatal(e)};return b}
func TestOriginalW16TypedDecoderAndLocalFK(t *testing.T){
 for _,profile:=range []string{"forward","outward"}{
  packet,ledger,e:=build(fixture(t),profile);if e!=nil{t.Fatal(profile,e)}
  if ledger.MaxAnalyticFKError>1e-8||!ledger.SyntheticTimeOnly||ledger.NativeSourceTimeAdmitted||
  ledger.ActualWeightedSkinAdmitted||len(packet.Actors)!=2{t.Fatal(ledger)}
  raw,e:=json.Marshal(packet);if e!=nil{t.Fatal(e)}
  if _,e=typed.Decode(raw);e!=nil{t.Fatal(e)}
  for _,a:=range packet.Actors{
   for _,f:=range a.Frames{if f.Foot.State!="unknown"||f.Foot.Anchor!=nil{
    t.Fatal("UNOBSERVED_CONTACT_FALSE_LABEL")
   }}
  }
 }
}
func TestSourceRejection(t *testing.T){
 raw:=fixture(t);var m map[string]interface{}
 if e:=json.Unmarshal(raw,&m);e!=nil{t.Fatal(e)}
 for _,key:=range []string{"source_rights","coordinate_basis","algorithm"}{
  x:=map[string]interface{}{};for k,v:=range m{x[k]=v}
  x[key]="UNADMITTED";b,_:=json.Marshal(x)
  if _,_,e:=build(b,"forward");e==nil{t.Fatal("BAD_"+key+"_ADMITTED")}
 }
 if _,_,e:=build(raw,"unverified");e==nil{t.Fatal("BAD_PROFILE_ADMITTED")}
}
func TestTypedClockAndContactNegatives(t *testing.T){
 p,_,e:=build(fixture(t),"forward");if e!=nil{t.Fatal(e)}
 p.Actors[0].Frames[1].TimeDen=nil
 if e:=typed.Validate(p);e==nil{t.Fatal("MISSING_TIME_ACCEPTED")}
 p,_,_=build(fixture(t),"forward")
 p.Actors[0].Frames[0].Foot.State="stance"
 if e:=typed.Validate(p);e==nil{t.Fatal("FABRICATED_STANCE_ACCEPTED_WITHOUT_ANCHOR")}
 p,_,_=build(fixture(t),"forward")
 p.Basis="BLENDER_Z_UP"
 if e:=typed.Validate(p);e==nil{t.Fatal("WRONG_AXIS_ACCEPTED")}
}
func TestQuatOrderAndAntipodal(t *testing.T){
 q,e:=between(Vec{0,-1,0},Vec{.2,-.9,.3});if e!=nil{t.Fatal(e)}
 v:=Vec{0,-1,0};a:=rotate(q,v)
 neg:=Quaternion{-q[0],-q[1],-q[2],-q[3]}
 if norm(minus(a,rotate(neg,v)))>1e-12{t.Fatal("ANTIPODAL_INCONSISTENT")}
 r:=Quaternion{q[3],q[0],q[1],q[2]} // Blender WXYZ as malformed glTF XYZW
 if norm(minus(rotate(r,v),a))<.01{t.Fatal("QUAT_COMPONENT_ORDER_FALSE_GREEN")}
}
