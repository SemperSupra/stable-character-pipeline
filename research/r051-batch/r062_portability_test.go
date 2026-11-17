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

func TestR062UnicodePathsAndStableOutput(t *testing.T){
  // Native PowerShell 5.1 and Linux must agree on the same offline Go CLI
  // while never echoing private path names or raw manifest/receipt contents.
  temp:=filepath.Join(t.TempDir(),"receipts space deutsch ไทย")
  if err:=os.MkdirAll(temp,0700);err!=nil{t.Fatal(err)}
  manifest:=filepath.Join(temp,"manifest prüfung.json")
  rep:=filepath.Join(temp,"résultat รายงาน actor.json")
  m,e:=json.Marshal(syntheticBatch());if e!=nil{t.Fatal(e)}
  r,e:=json.Marshal(syntheticRep());if e!=nil{t.Fatal(e)}
  if e=os.WriteFile(manifest,m,0600);e!=nil{t.Fatal(e)}
  if e=os.WriteFile(rep,r,0600);e!=nil{t.Fatal(e)}
  command:=exec.Command("go","run",".","--manifest",manifest,"--rep",rep)
  command.Env=append(os.Environ(),"GOPROXY=off","GOSUMDB=off","GOTOOLCHAIN=local")
  out,err:=command.CombinedOutput()
  if err!=nil{t.Fatalf("unicode-path CLI failed: %v output=%s",err,out)}
  if !bytes.Contains(out,[]byte("R061_OFFLINE_ACTOR_REP_REVIEW"))||
     !bytes.Contains(out,[]byte("STRUCTURALLY_VALID_SELF_REPORT_NOT_INDEPENDENTLY_VERIFIED")) {
      t.Fatalf("unicode-path result contract invalid: %s",out)
  }
  if bytes.Contains(out,[]byte(temp))||bytes.Contains(out,[]byte(manifest))||bytes.Contains(out,[]byte(rep)) {
     t.Fatal("successful receipt CLI leaked source path")
  }
}

func TestR062AdversarialInputs(t *testing.T){
  t.Parallel()
  cases:=map[string][]byte{
    "invalid-utf8":append([]byte(`{"actor":"`),0xff,0xfe,'"','}'),
    "escaped-duplicate-root":[]byte(`{"schema":"first","schema":"second"}`),
    "escaped-duplicate-nested":[]byte(`{"packets":[{"id":"x","id":"y"}]}`),
    "max-nesting":append(bytes.Repeat([]byte("["),66),bytes.Repeat([]byte("]"),66)...),
    "two-documents":[]byte(`{"schema":"x"}{"schema":"y"}`),
    "unknown-owner-override":[]byte(`{"schema":"x","owner_approved":true}`),
  }
  for n,v:=range cases{
    t.Run(n,func(t *testing.T){
      t.Parallel()
      f:=filepath.Join(t.TempDir(),"suspicious.json")
      if err:=os.WriteFile(f,v,0600);err!=nil{t.Fatal(err)}
      var observation ActorRep
      if err:=decodeLocalBounded(f,&observation);err==nil{
         t.Fatal("adversarial local input was admitted")
      }
    })
  }
}

func TestR062ActorExhaustionNeverPromoted(t *testing.T){
  t.Parallel()
  rep:=cloneRep(syntheticRep())
  rep.Packets[0]=PacketResult{ID:"SYN-A",State:"NOT_RUN",Branch:"research/r051-a",
    SourceSHA:strings.Repeat("a",40),NextBlocker:"LOCAL_ACTOR_CAPACITY_EXHAUSTED"}
  rep.Packets[1]=PacketResult{ID:"SYN-B",State:"NOT_RUN",Branch:"research/r051-b",
    SourceSHA:strings.Repeat("b",40),NextBlocker:"LOCAL_ACTOR_CAPACITY_EXHAUSTED"}
  observed,err:=ValidateActorRep(syntheticBatch(),rep)
  if err!=nil{t.Fatal(err)}
  if observed.ReportedExecuted!=0||observed.ReportedNotRun!=2||
    observed.Status!="STRUCTURALLY_VALID_SELF_REPORT_NOT_INDEPENDENTLY_VERIFIED"{
       t.Fatalf("actor progress invented from self-report: %+v",observed)
  }
}
