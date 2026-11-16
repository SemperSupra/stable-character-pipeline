package main

import (
    "bytes"
    "encoding/json"
    "os"
    "os/exec"
    "path/filepath"
    "strings"
    "testing"
)

func TestR061StrictJSON(t *testing.T) {
    t.Parallel()
    cases:=map[string]string{
        "duplicate-root":`{"id":"one","id":"two"}`,
        "duplicate-nested":`{"packets":[{"id":"one","id":"two"}]}`,
        "trailing":`{"id":"one"} {"id":"two"}`,
        "unknown-field":`{"invented_owner_approval":true}`,
        "malformed":`{"id":"oops"`,
        "too-large":strings.Repeat("x",(1<<20)+1),
    }
    for name,raw:=range cases{
        t.Run(name,func(t *testing.T){
            t.Parallel()
            f:=filepath.Join(t.TempDir(),"input.json")
            if err:=os.WriteFile(f,[]byte(raw),0600);err!=nil{t.Fatal(err)}
            var data ActorRep
            if err:=decodeLocalBounded(f,&data);err==nil{
                t.Fatal("malformed or unsafe JSON falsely admitted")
            }
        })
    }
    valid:=filepath.Join(t.TempDir(),"valid.json")
    raw,err:=json.Marshal(syntheticRep())
    if err!=nil{t.Fatal(err)}
    if err:=os.WriteFile(valid,raw,0600);err!=nil{t.Fatal(err)}
    var decoded ActorRep
    if err:=decodeLocalBounded(valid,&decoded);err!=nil{t.Fatal(err)}
    if decoded.Schema!=RepSchema||len(decoded.Packets)!=3{t.Fatal("valid rep lost")}
}
func TestR061OfflineCLI(t *testing.T) {
    batchRaw,err:=json.Marshal(syntheticBatch())
    if err!=nil{t.Fatal(err)}
    repRaw,err:=json.Marshal(syntheticRep())
    if err!=nil{t.Fatal(err)}
    temp:=t.TempDir()
    manifest:=filepath.Join(temp,"batch.json")
    rep:=filepath.Join(temp,"rep.json")
    if err:=os.WriteFile(manifest,batchRaw,0600);err!=nil{t.Fatal(err)}
    if err:=os.WriteFile(rep,repRaw,0600);err!=nil{t.Fatal(err)}
    invoke:=func(args ...string)([]byte,error){
        cmd:=exec.Command("go",append([]string{"run","."},args...)...)
        cmd.Env=append(os.Environ(),"GOTOOLCHAIN=local","GOPROXY=off","GOSUMDB=off")
        return cmd.CombinedOutput()
    }
    out,err:=invoke("--manifest",manifest)
    if err!=nil||!bytes.Contains(out,[]byte("R051_BATCH_CONTRACT_RECEIPT")){
        t.Fatalf("legacy manifest-only CLI contract broken: %v: %s",err,out)
    }
    out,err=invoke("--manifest",manifest,"--rep",rep)
    if err!=nil||!bytes.Contains(out,[]byte("R061_OFFLINE_ACTOR_REP_REVIEW"))||
      !bytes.Contains(out,[]byte("STRUCTURALLY_VALID_SELF_REPORT_NOT_INDEPENDENTLY_VERIFIED")){
        t.Fatalf("bounded rep CLI failed: %v: %s",err,out)
    }
    // A malicious duplicate field must produce typed nonzero failure,
    // not last-wins silent identity or owner policy overwrite.
    if err:=os.WriteFile(rep,[]byte(`{"schema":"valid","schema":"attacker"}`),0600);err!=nil{t.Fatal(err)}
    out,err=invoke("--manifest",manifest,"--rep",rep)
    if err==nil||!bytes.Contains(out,[]byte("R060_REP_HOLD")) {
        t.Fatalf("duplicate-key attack did not produce typed CLI failure: %v: %s",err,out)
    }
}
