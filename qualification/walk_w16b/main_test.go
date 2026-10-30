package main
import (
 "bytes"
 "encoding/json"
 "os"
 "testing"
)
func fixture(t *testing.T)[]byte{t.Helper();b,e:=os.ReadFile("fixtures_w13a_pinned.json");if e!=nil{t.Fatal(e)};return b}
func TestIndependentJoin(t *testing.T){
 r,e:=Run(fixture(t));if e!=nil{t.Fatal(e)}
 if r.ReachableCompared!=4||r.UnreachablePolicyDifferences!=1||r.MaxKneeError>1e-8{t.Fatal(r)}
 flagged:=0
 for _,c:=range r.Cases{if c.BStatus=="REACHED"&&c.ChildLocalMisuseError>1e-5{flagged++}}
 if flagged==0{t.Fatal("WORLD_QUAT_AS_CHILD_LOCAL_FALSE_GREEN")}
}
func TestHostileAdmission(t *testing.T){
 raw:=fixture(t)
 var original map[string]interface{}
 if e:=json.Unmarshal(raw,&original);e!=nil{t.Fatal(e)}
 for _,tc:=range []struct{name,key string;value interface{}}{
  {"rights","source_rights","UNVERIFIED"},
  {"basis","coordinate_basis","BLENDER_Z_UP"},
  {"units","units","METERS"},
  {"scope","algorithm","UNREVIEWED"},
  {"set","cases",[]interface{}{}},
 }{
  t.Run(tc.name,func(t *testing.T){
   m:=map[string]interface{}{}
   for k,v:=range original{m[k]=v}
   m[tc.key]=tc.value;b,_:=json.Marshal(m)
   if _,e:=Run(b);e==nil{t.Fatal("HOSTILE_ACCEPTED")}
  })
 }
 t.Run("unknown_field",func(t *testing.T){
  b:=bytes.Replace(raw,[]byte("\"schema\":"),[]byte("\"forged\":1,\"schema\":"),1)
  if _,e:=Run(b);e==nil{t.Fatal("UNKNOWN_FIELD_ACCEPTED")}
 })
 t.Run("trailing_json",func(t *testing.T){
  b:=append(append([]byte{},raw...),raw...)
  if _,e:=Run(b);e==nil{t.Fatal("TRAILING_JSON_ACCEPTED")}
 })
}
