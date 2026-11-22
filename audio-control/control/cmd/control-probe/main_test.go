package main

import (
 "bytes"
 "encoding/json"
 "strings"
 "testing"
)
func TestCapabilityCLI(t *testing.T){
 var b bytes.Buffer
 if err:=run([]string{"capabilities"},strings.NewReader(""),&b);err!=nil{t.Fatal(err)}
 var m map[string]any
 if e:=json.Unmarshal(b.Bytes(),&m);e!=nil{t.Fatal(e)}
 if m["can_play_physical_audio"]!=false||m["is_production"]!=false{
  t.Fatalf("capability overstated: %s",b.String())
 }
}
func TestSimulationCannotForgeHostEvent(t *testing.T){
 var b bytes.Buffer
 line:=`{"schema_version":"audio_control.r0","principal_id":"synthetic","session_id":"s","target_id":"t","operation_id":"attempt","action":"host_started","expected_revision":0,"epoch":1}`
 if err:=run([]string{"simulate"},strings.NewReader(line+"\n"),&b);err!=nil{t.Fatal(err)}
 if !strings.Contains(b.String(),"host_observation_requires_trusted_adapter"){
  t.Fatalf("forged host claim accepted: %s",b.String())
 }
}
func TestUnknownJSONFieldFailsClosed(t *testing.T){
 var b bytes.Buffer
 line:=`{"schema_version":"audio_control.r0","principal_id":"p","session_id":"s","target_id":"t","operation_id":"id","action":"stop","expected_revision":0,"magic_play":true}`
 if err:=run([]string{"simulate"},strings.NewReader(line+"\n"),&b);err==nil{
  t.Fatal("unknown field silently allowed")
 }
}
