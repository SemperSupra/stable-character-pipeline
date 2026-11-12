package main

import (
    "bytes"
    "encoding/json"
    "os"
    "strings"
    "testing"
)
func load(t *testing.T) Catalog {
    t.Helper()
    b,err:=os.ReadFile("fixtures.json");if err!=nil {t.Fatal(err)}
    var c Catalog
    if err=json.Unmarshal(b,&c);err!=nil {t.Fatal(err)}
    return c
}
func check(t *testing.T,c Catalog,wantReject bool) {
    t.Helper()
    b,err:=json.Marshal(c);if err!=nil {t.Fatal(err)}
    _,err=Validate(b)
    if wantReject && err==nil {t.Fatal("expected rejection")}
    if !wantReject && err!=nil {t.Fatal(err)}
}
func TestValid(t *testing.T){check(t,load(t),false)}
func TestDuplicate(t *testing.T){c:=load(t);c.Items[1].ID=c.Items[0].ID;check(t,c,true)}
func TestWrongRatio(t *testing.T){c:=load(t);c.Items[1].WaistHipRatio+=0.1;check(t,c,true)}
func TestOmittedAdult(t *testing.T){c:=load(t);c.Items[0].AdultState="";check(t,c,true)}
func TestBadIndex(t *testing.T){c:=load(t);c.Items[0].Fullness=1.02;check(t,c,true)}
func TestUnexpectedNativeMHRMapping(t *testing.T){c:=load(t);c.Items[0].NativeMHR=[]byte(`{"shape0":0.8}`);check(t,c,true)}
func TestUnexpectedNativeMPFBMapping(t *testing.T){c:=load(t);c.Items[0].NativeMPFB=[]byte(`{"height":0.4}`);check(t,c,true)}
func TestMissingMapField(t *testing.T){
    b,err:=os.ReadFile("fixtures.json");if err!=nil {t.Fatal(err)}
    b=bytes.Replace(b,[]byte(`"native_mhr_map": null,`),[]byte(""),1)
    if _,err=Validate(b);err==nil {t.Fatal("missing native-map field accepted")}
}
func TestUnexpectedPolicyField(t *testing.T){
    b,err:=os.ReadFile("fixtures.json");if err!=nil {t.Fatal(err)}
    b=bytes.Replace(b,[]byte(`"schema": 1,`),[]byte(`"schema": 1, "allow": true,`),1)
    if _,err=Validate(b);err==nil {t.Fatal("unknown policy field accepted")}
}
func TestTrailingJSON(t *testing.T){
    b,err:=os.ReadFile("fixtures.json");if err!=nil {t.Fatal(err)}
    b=append(b,[]byte("\n{}\n")...)
    if _,err=Validate(b);err==nil {t.Fatal("trailing object accepted")}
}
func TestNoSensitiveTerms(t *testing.T){
    b,err:=os.ReadFile("fixtures.json");if err!=nil {t.Fatal(err)}
    for _,s:=range []string{"loli","childlike","sexualized","protected_person"} {
        if strings.Contains(strings.ToLower(string(b)),s) {t.Fatalf("unexpected %q",s)}
    }
}
