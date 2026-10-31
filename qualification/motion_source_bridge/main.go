// Source-only, non-promoting C1/C5 evidence bridge. No raw motion, identity or historical score is inferred.
package main

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "math/big"
 "os"
 "sort"
)
const bookHash="7294644f1fc26490f8a0aed415afc01b8278294e4373169e1407986c56cb0961"
const edition="pg:12926@1d5ca33372491509805a64cd0425a5164d3108fa"
func object(x any)map[string]any{v,_:=x.(map[string]any);return v}
func field(m map[string]any,k string)string{v,_:=m[k].(string);return v}
func number(m map[string]any,k string)int64{n,_:=m[k].(json.Number);v,_:=n.Int64();return v}
func array(m map[string]any,k string)[]any{a,_:=m[k].([]any);return a}
func validateJSON(raw []byte)(map[string]any,error){
 d:=json.NewDecoder(bytes.NewReader(raw));d.UseNumber()
 var visit func()error
 visit=func()error{
  v,e:=d.Token();if e!=nil{return e}
  sep,ok:=v.(json.Delim);if !ok{return nil}
  switch sep{
  case '{':
   seen:=map[string]bool{}
   for d.More(){
    k,e:=d.Token();if e!=nil{return e}
    key,ok:=k.(string);if !ok||seen[key]{return errors.New("duplicate JSON key")}
    seen[key]=true
    if e=visit();e!=nil{return e}
   }
   _,e:=d.Token();return e
  case '[':
   for d.More(){if e:=visit();e!=nil{return e}}
   _,e:=d.Token();return e
  default:return errors.New("unexpected JSON delimiter")
  }
 }
 if e:=visit();e!=nil{return nil,e}
 if _,e:=d.Token();e!=io.EOF{return nil,errors.New("extra JSON value")}
 var result map[string]any
 d=json.NewDecoder(bytes.NewReader(raw));d.UseNumber()
 if e:=d.Decode(&result);e!=nil{return nil,e}
 if result==nil{return nil,errors.New("not an object")}
 return result,nil
}
func validFigure(f map[string]any)error{
 if field(f,"schema")!="scp.source-figure-first-pass.v0"||field(f,"source_sha256")!=bookHash||field(f,"source_edition")!=edition||field(f,"name")!="Cross-over"||number(f,"written_bars")!=8||number(f,"figure_start_line")!=1433||number(f,"figure_end_line")!=1467{return errors.New("unverified historical figure identity")}
 for k,want:=range map[string]string{
  "text_status":"SOURCE_SPANS_CHECKED_FIRST_PASS_NOT_INDEPENDENT_GOLD",
  "diagrams_status":"ILLUSTRATIONS_NOT_DIGITALLY_QUALIFIED",
  "music_score_status":"NO_NOTATED_SCORE_BYTES_ADMITTED",
  "independent_review":"PENDING_SECOND_READER",
  "physical_motion":"UNKNOWN_NOT_MEASURED",
 }{if field(f,k)!=want{return fmt.Errorf("overclaimed source status: %s",k)}}
 ids:=map[string][2]string{
  "figure-eight-bars":{"1-8","SOURCE_TEXT_ONLY"},
  "partner-cross":{"1-2","DIRECTION_AND_PARTNER_NOT_A_JOINT_PATH"},
  "right-shoulder-rule":{"1-8","SOURCE_TEXT_RULE_NO_CONTACT_CLAIM"},
  "right-turn-inward":{"3-4","SOURCE_TEXT_ONLY"},
  "recross":{"5-6","SOURCE_TEXT_ONLY"},
  "right-turn-front":{"7-8","SOURCE_TEXT_ONLY"},
  "half-bar-jump-cue":{"4,8","HALF_BAR_CUE_NO_KINEMATIC_CLAIM"},
 }
 cues:=array(f,"phrases");if len(cues)!=7{return errors.New("figure cue count")}
 seen:=map[string]bool{}
 for _,v:=range cues{
  p:=object(v);id:=field(p,"id");ref,ok:=ids[id]
  if !ok||seen[id]||field(p,"bars")!=ref[0]||field(p,"interpretation_status")!=ref[1]||field(p,"anchor")==""||number(p,"start_line")<1433||number(p,"end_line")>1467||number(p,"end_line")<number(p,"start_line"){return errors.New("unverified/overclaimed figure cue")}
  seen[id]=true
 }
 return nil
}
func validScore(s map[string]any)error{
 hash:=field(s,"source_audio_project_sha256")
 decoded,e:=hex.DecodeString(hash)
 if e!=nil||len(decoded)!=32||hex.EncodeToString(decoded)!=hash||field(s,"schema")!="scp.synthetic.score-audio-time-map.v0"||field(s,"timebase")!="480_MIDI_TICKS_PER_QUARTER_EXACT_RATIONAL"||field(s,"audio_verification")!="SYNTHETIC_SCORE_TIMEMAP_ONLY_AUDIO_WAVEFORM_NOT_CHECKED"||s["performed_audio_accepted"]!=false||number(s,"original_source_audio_rate")!=48000{return errors.New("score provenance/time scope inconsistent")}
 ev:=array(s,"events");if len(ev)<1||len(ev)>256{return errors.New("score event count")}
 seen:=map[string]bool{}
 for _,v:=range ev{
  x:=object(v);id:=field(x,"id");actor:=field(x,"actor_id");tick:=number(x,"tick")
  if id==""||seen[id]||(actor!="actor-a"&&actor!="actor-b")||tick<0||tick>15360||field(x,"evidence_status")!="ORIGINAL_SYNTHETIC_TIME_PROPOSAL_NO_MEASURED_MOTION"{return errors.New("actor/clock/observation claim invalid")}
  seen[id]=true
  seconds,ok:=new(big.Rat).SetString(field(x,"exact_seconds"));if !ok||seconds.Sign()<0{return errors.New("invalid rational seconds")}
  samples,ok:=new(big.Rat).SetString(field(x,"exact_sample_position"));if !ok||samples.Sign()<0{return errors.New("invalid rational samples")}
  if new(big.Rat).Mul(seconds,big.NewRat(48000,1)).Cmp(samples)!=0{return errors.New("sample/seconds mismatch")}
 }
 return nil
}
func bridge(a,b []byte)(map[string]any,error){
 f,e:=validateJSON(a);if e!=nil{return nil,e}
 s,e:=validateJSON(b);if e!=nil{return nil,e}
 if e=validFigure(f);e!=nil{return nil,e}
 if e=validScore(s);e!=nil{return nil,e}
 fh:=sha256.Sum256(a);sh:=sha256.Sum256(b)
 return map[string]any{
 "schema":"scp.motion-source-evidence-bridge.v0",
 "figure_receipt_sha256":hex.EncodeToString(fh[:]),
 "score_receipt_sha256":hex.EncodeToString(sh[:]),
 "book_source_claim_sha256":bookHash,
 "synthetic_score_project_claim_sha256":field(s,"source_audio_project_sha256"),
 "source_cues":7,"source_bars":8,"score_events":len(array(s,"events")),
 "qualification":"PASS_METADATA_NONPROMOTING_ONLY",
 "admission":"NOT_ADMITTED",
 "holds":[]string{"not_independently_rehashed_source_bytes","second_reader_and_diagram_missing","actor_count_and_roles_unknown","historical_score_not_admitted","no_cross_source_figure_to_score_alignment","synthetic_time_not_measured_motion","no_anatomy_contact_rig_or_R009_admission"},
 "audiences":[]string{"human_readme","automation_json","agent_read_only_capabilities"},
 },nil
}
func read(path string)([]byte,error){
 f,e:=os.Open(path);if e!=nil{return nil,e};defer f.Close()
 a,e:=io.ReadAll(io.LimitReader(f,1048577));if e!=nil{return nil,e}
 if len(a)==0||len(a)>1048576{return nil,errors.New("input size outside 1 MiB cap")}
 return a,nil
}
func main(){
 figure:=flag.String("figure","","first-pass source JSON");score:=flag.String("score","","synthetic score JSON");capabilities:=flag.Bool("capabilities",false,"read-only agent discovery");flag.Parse()
 if *capabilities{
  _=json.NewEncoder(os.Stdout).Encode(map[string]any{"schema":"scp.motion-source-evidence-bridge.v0","actions":[]string{"validate-metadata-only"},"denied":[]string{"source-admission","motion-inference","concept-promotion","release"}});return
 }
 if *figure==""||*score==""{fmt.Fprintln(os.Stderr,"-figure and -score required");os.Exit(2)}
 a,e:=read(*figure);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}
 b,e:=read(*score);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}
 r,e:=bridge(a,b);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}
 sort.Strings(r["holds"].([]string))
 enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ");if e:=enc.Encode(r);e!=nil{os.Exit(1)}
}
