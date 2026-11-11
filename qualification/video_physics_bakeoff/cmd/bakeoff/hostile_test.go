package main

import (
 "encoding/json"
 "os"
 "path/filepath"
 "testing"
)
func TestMalformedUnknownIsNotOracleMatch(t *testing.T) {
 d:=t.TempDir(); if e:=os.WriteFile(filepath.Join(d,"invalid.json"),[]byte("{"),0600);e!=nil{t.Fatal(e)}
 r:=evaluate(d,Case{ID:"malformed",Kind:"motion",Path:"invalid.json",Expect:"UNKNOWN"})
 if r.Error==""||r.MatchesOracle{t.Fatalf("parse error hidden by expected UNKNOWN: %+v",r)}
}
func TestUnsupportedKindCannotMasqueradeAsUnknown(t *testing.T) {
 d:=t.TempDir();os.WriteFile(filepath.Join(d,"exists.bin"),[]byte("public"),0600)
 r:=evaluate(d,Case{ID:"bad-kind",Kind:"unrecognized",Path:"exists.bin",Expect:"UNKNOWN"})
 if r.Error==""||r.MatchesOracle{t.Fatalf("unsupported case passed: %+v",r)}
}
func TestEscapingSymlinkRejected(t *testing.T) {
 d:=t.TempDir();outside:=t.TempDir()
 os.WriteFile(filepath.Join(outside,"source.json"),[]byte("{}"),0600)
 if e:=os.Symlink(filepath.Join(outside,"source.json"),filepath.Join(d,"alias.json"));e!=nil{t.Skipf("symlink unsupported: %v",e)}
 r:=evaluate(d,Case{ID:"escape",Kind:"motion",Path:"alias.json",Expect:"UNKNOWN"})
 if r.Error==""||r.MatchesOracle{t.Fatalf("source path escaped fixture root: %+v",r)}
}
func TestMissingUnknownProducesNonzeroAndReceipt(t *testing.T) {
 d:=t.TempDir()
 b,_:=json.Marshal(Manifest{Schema:"scp.video-bakeoff-cases.v1",Cases:[]Case{{ID:"missing",Kind:"motion",Path:"not-present.json",Expect:"UNKNOWN"}}})
 manifest:=filepath.Join(d,"cases.json");out:=filepath.Join(d,"receipt.json")
 if e:=os.WriteFile(manifest,b,0600);e!=nil{t.Fatal(e)}
 if e:=run(manifest,out);e==nil{t.Fatalf("missing observation must not qualify as expected UNKNOWN")}
 receiptBytes,e:=os.ReadFile(out);if e!=nil{t.Fatal(e)}
 var r Receipt;if e:=json.Unmarshal(receiptBytes,&r);e!=nil{t.Fatal(e)}
 if r.Matched!=0||r.Discrepancies!=1{t.Fatalf("incorrect fail-closed receipt %+v",r)}
}
