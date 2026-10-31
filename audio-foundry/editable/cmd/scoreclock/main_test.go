package main
import(
 "bytes"
 "encoding/json"
 "strings"
 "testing"
)
func TestCLIParityAndNegative(t *testing.T){
 var out bytes.Buffer
 if err:=execute([]string{"-capabilities"},&out);err!=nil{t.Fatal(err)}
 var m map[string]any
 if err:=json.Unmarshal(out.Bytes(),&m);err!=nil{t.Fatal(err)}
 if m["schema"]!="scp.synthetic.score-audio-time-map.v0"{t.Fatalf("wrong capability %+v",m)}
 out.Reset()
 if err:=execute([]string{"-fixture"},&out);err!=nil{t.Fatal(err)}
 b:=append([]byte(nil),out.Bytes()...);out.Reset()
 if err:=execute([]string{"-fixture"},&out);err!=nil{t.Fatal(err)}
 if !bytes.Equal(b,out.Bytes()){t.Fatal("fixture not idempotent")}
 var p map[string]any;if err:=json.Unmarshal(b,&p);err!=nil{t.Fatal(err)}
 if p["audio_verification"]!="SYNTHETIC_SCORE_TIMEMAP_ONLY_AUDIO_WAVEFORM_NOT_CHECKED"{t.Fatal("fabricated audio proof")}
 out.Reset()
 for _,args:=range [][]string{{"-project","missing.json"},{"-fixture","-capabilities"},{"-request","missing.json"},{"-project","missing.json","-request","missing.json"}}{
  if err:=execute(args,&out);err==nil{t.Fatal("invalid command passed")}
  if out.Len()!=0{t.Fatal("error produced partial JSON")}
 }
 if err:=execute([]string{"-unexpected"},&out);err==nil||!strings.Contains(err.Error(),"not defined"){t.Fatalf("bad flag allowed %v",err)}
}
