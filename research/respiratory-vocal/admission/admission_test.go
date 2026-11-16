package admission
import("bytes";"encoding/json";"strings";"testing"
"github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/behavior")
func healthy()[]byte{
 p:=behavior.Performance{Schema:behavior.Schema,Classification:behavior.Classification,SampleRateHz:behavior.Rate,Action:behavior.QuietBreath,Frames:[]behavior.Frame{{StartSample:0,EndSample:4800,Phase:behavior.Expiration,Route:behavior.Oral,OralFlowM3S:.0001,TotalFlowM3S:.0001,MouthFreeOpening:true,DevicePort:behavior.NoPort,Sources:[]behavior.Source{{Kind:behavior.AirflowNoise,Amplitude:.2}}}}}
 b,e:=json.Marshal(p);if e!=nil{panic(e)};return b
}
func TestValidSourceFixtureAndReplay(t *testing.T){
 b:=healthy()
 p,e:=Decode(b);if e!=nil{t.Fatal(e)}
 if p.Action!=behavior.QuietBreath||p.Frames[0].TotalFlowM3S!=.0001{t.Fatalf("wrong source parsed %+v",p)}
 if _,e=Decode(append([]byte(" \n\t"),b...));e!=nil{t.Fatalf("valid whitespace denied: %v",e)}
}
func TestMalformedOrPrivateEventsFailClosed(t *testing.T){
 valid:=string(healthy())
 replace:=func(old,new string)string{if !strings.Contains(valid,old){t.Fatalf("test fixture missing %s",old)};return strings.Replace(valid,old,new,1)}
 cases:=[]string{
  replace(`"classification":"PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL"`,`"classification":"PRIVATE_FINAL_CHARACTER_VOICE"`),
  replace(`"schema":"respiratory.performance.v0"`,`"schema":"other"`),
  replace(`"sample_rate_hz":48000`,`"sample_rate_hz":"48000"`),
  replace(`"oral_free_flow_m3_s":0.0001`,`"oral_free_flow_m3_s":-0.0001`),
  replace(`"sample_rate_hz":48000`,`"sample_rate_hz":48000,"sample_rate_hz":96000`),
  replace(`"phase":"expiration"`,`"phase":"expiration","phase":"inspiration"`),
  replace(`"kind":"airflow_turbulence"`,`"kind":"airflow_turbulence","kind":"glottal_voiced"`),
  replace(`"external_port":"none"`,`"external_port":"none","private_raw_audio":"private"`),
  strings.TrimSuffix(valid,"}")+`,"unreviewed_reference":"private" }`,
  valid+` {"second":true}`,
  `{"schema":"respiratory.performance.v0","frames":[{"a":{"b":0,"b":1}}]}`,
  strings.Repeat(" ",MaxPayloadBytes+1),
  strings.Repeat("[",MaxDepth+2)+"0"+strings.Repeat("]",MaxDepth+2),
 }
 for i,s:=range cases{if _,e:=Decode([]byte(s));e==nil{t.Fatalf("negative fixture %d unexpectedly accepted",i)}}
 if _,e:=Decode(append(healthy(),0xff));e==nil{t.Fatal("bad UTF-8 accepted")}
}
func TestSemanticConservationAndTopology(t *testing.T){
 p,e:=Decode(healthy());if e!=nil{t.Fatal(e)}
 p.Frames[0].TotalFlowM3S+=.00005
 b,e:=json.Marshal(p);if e!=nil{t.Fatal(e)}
 if _,e:=Decode(b);e==nil{t.Fatal("branch mismatch admitted")}
 p.Frames[0].TotalFlowM3S-=.00005
 p.Frames[0].DevicePort=behavior.Flute
 b,e=json.Marshal(p);if e!=nil{t.Fatal(e)}
 if _,e:=Decode(b);e==nil{t.Fatal("object attached to wrong route")}
}
func TestRecursiveDuplicateScannerAndIndependentObjectScopes(t *testing.T){
 if e:=CheckJSON([]byte(`{"a":{"b":[{"c":0,"c":1}]}}`));e==nil{t.Fatal("nested dup admitted")}
 if e:=CheckJSON([]byte(`{"a":[{"x":0},{"x":1}]}`));e!=nil{t.Fatal("nonduplicate across objects was denied")}
}
func FuzzAdmissionNeverPanics(f *testing.F){
 f.Add(healthy());f.Add([]byte(`{"a":{"a":0,"a":1}}`));f.Add([]byte(nil));f.Add([]byte(`{"frames":[{}]}`))
 f.Fuzz(func(t *testing.T,data []byte){
  if len(data)>MaxPayloadBytes{t.Skip()}
  p,e:=Decode(data)
  if e==nil{
   b,err:=json.Marshal(p);if err!=nil{t.Fatal(err)}
   if !bytes.Equal(bytes.TrimSpace(data),b){
    if _,err=Decode(b);err!=nil{t.Fatalf("accepted event cannot be replayed: %v",err)}
   }
  }
 })
}
