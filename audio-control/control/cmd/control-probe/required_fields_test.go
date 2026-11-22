package main

import (
 "bytes"
 "encoding/json"
 "strings"
 "testing"
)

func TestRequiredCommandFieldsCannotDefaultOrBeNull(t *testing.T) {
 base := map[string]any{
  "schema_version":"audio_control.r0", "principal_id":"p", "session_id":"s",
  "target_id":"t", "operation_id":"op", "action":"configure",
  "expected_revision":0, "config_digest":strings.Repeat("a",64),
 }
 for _, field := range []string{"schema_version","principal_id","session_id","target_id","operation_id","action","expected_revision","config_digest"} {
  for _, mode := range []string{"absent","null"} {
   t.Run(field+"/"+mode,func(t *testing.T) {
    candidate:=make(map[string]any)
    for k,v:=range base { candidate[k]=v }
    if mode=="absent" { delete(candidate,field) } else { candidate[field]=nil }
    raw,err:=json.Marshal(candidate);if err!=nil { t.Fatal(err) }
    var output bytes.Buffer
    if err:=run([]string{"simulate"},bytes.NewReader(raw),&output);err==nil {
     t.Fatal("missing/null required field accepted")
    }
    if output.Len()!=0 { t.Fatal("invalid envelope reached reducer/output") }
   })
  }
 }
 var output bytes.Buffer
 raw,_:=json.Marshal(base)
 if err:=run([]string{"simulate"},bytes.NewReader(raw),&output);err!=nil { t.Fatalf("explicit zero revision rejected: %v",err) }
 if !strings.Contains(output.String(),"\"accepted\"") { t.Fatalf("valid command not accepted: %s",output.String()) }
}
