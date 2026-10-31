package editable

// Original-synthetic source-score to audio-sample *time map* only.
// Audio Foundry editable_audio.v1 renders a constant BPM source. Tempo changes
// here are not proof of a changed audio waveform or score-performance fit.
import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "math/big"
 "sort"
 "strings"
)
const AlignmentSchema="scp.synthetic.score-audio-time-map.v0"
type TempoPoint struct {
 AtTick int64 `json:"at_tick"`
 BPM int64 `json:"bpm"`
}
type ChoreographyEvent struct {
 ID string `json:"id"`
 ActorID string `json:"actor_id"`
 Role string `json:"role"`
 Action string `json:"action"`
 Tick int64 `json:"tick"`
}
type ScoreRequest struct {
 Schema string `json:"schema"`
 Origin string `json:"origin"`
 AudioProjectSHA256 string [[audio_project_sha256]]
 Tempo []TempoPoint `json:"tempo"`
 Events []ChoreographyEvent `json:"events"`
}
type ScoreEvent struct {
 ChoreographyEvent
 ExactSamplePosition string `json:"exact_sample_position"`
 ExactSeconds string `json:"exact_seconds"`
 EvidenceStatus string `json:"evidence_status"`
}
type ScoreTimeMap struct {
 Schema string `json:"schema"`
 SourceAudioProjectSHA256 string [[source_audio_project_sha256]]
 Meter string `json:"meter"`
 Timebase string `json:"timebase"`
 AudioVerification string `json:"audio_verification"`
 Events []ScoreEvent `json:"events"`
 ContentID string `json:"content_id"`
}
func PublicAudioHash(p Project)(string,error){
 b,err:=p.Bytes();if err!=nil{return "",err}
 sum:=sha256.Sum256(b);return hex.EncodeToString(sum[:]),nil
}
func validID(s string) bool{
 if s==""||len(s)>80{return false}
 for _,r:=range s{if !(r>='a'&&r<='z'||r>='A'&&r<='Z'||r>='0'&&r<='9'||r=='-'||r=='_'){return false}}
 return true
}
func validRequest(p Project,r ScoreRequest)error{
 if err:=p.Validate();err!=nil{return err}
 sum,err:=PublicAudioHash(p);if err!=nil{return err}
 if r.Schema!=AlignmentSchema||r.Origin!="ORIGINAL_SYNTHETIC"||r.AudioProjectSHA256!=sum{return errors.New("source schema, original-only classification or project digest invalid")}
 if len(r.Tempo)<1||len(r.Tempo)>32||len(r.Events)<1||len(r.Events)>256{return errors.New("tempo/event bounds")}
 limit:=int64(p.Beats)*PPQ
 for i,tp:=range r.Tempo{
  if tp.BPM<40||tp.BPM>240||tp.AtTick<0||tp.AtTick>=limit||tp.AtTick%PPQ!=0{return errors.New("unsupported tempo point")}
  if i==0{if tp.AtTick!=0||tp.BPM!=int64(p.BPM){return errors.New("first tempo must match original audio source BPM")}}
  if i>0&&r.Tempo[i-1].AtTick>=tp.AtTick{return errors.New("out of order or duplicate tempo")}
 }
 seen:=map[string]bool{}
 for _,e:=range r.Events{
  if !validID(e.ID)||seen[e.ID]||e.ActorID!="actor-a"&&e.ActorID!="actor-b"||e.Tick<0||e.Tick>limit{return errors.New("invalid ID, actor or event tick")}
  seen[e.ID]=true
  if e.Role!="leader"&&e.Role!="follower"&&e.Role!="solo"{return errors.New("role not in original synthetic vocab")}
  switch e.Action{case "step","turn","hold","cross","clap":default:return errors.New("unknown synthetic action")}
 }
 return nil
}
func ExactSecondsAt(tick int64,tempos []TempoPoint)(*big.Rat,error){
 if tick<0||len(tempos)==0||tempos[0].AtTick!=0{return nil,errors.New("unanchored tick")}
 elapsed:=new(big.Rat)
 for i,t:=range tempos{
  if t.BPM<=0||t.AtTick>tick{break}
  end:=tick
  if i+1<len(tempos)&&tempos[i+1].AtTick<end{end=tempos[i+1].AtTick}
  if end<t.AtTick{return nil,errors.New("invalid tempo interval")}
  delta:=end-t.AtTick
  numerator:=new(big.Int).Mul(big.NewInt(delta),big.NewInt(60))
  denominator:=new(big.Int).Mul(big.NewInt(t.BPM),big.NewInt(PPQ))
  elapsed.Add(elapsed,new(big.Rat).SetFrac(numerator,denominator))
  if end==tick{break}
 }
 return elapsed,nil
}
func AlignOriginalSynthetic(p Project,r ScoreRequest)(ScoreTimeMap,error){
 if err:=validRequest(p,r);err!=nil{return ScoreTimeMap{},err}
 ordered:=append([]ChoreographyEvent(nil),r.Events...)
 sort.Slice(ordered,func(i,j int)bool{if ordered[i].Tick!=ordered[j].Tick{return ordered[i].Tick<ordered[j].Tick};return ordered[i].ID<ordered[j].ID})
 out:=ScoreTimeMap{Schema:AlignmentSchema,SourceAudioProjectSHA256:r.AudioProjectSHA256,Meter:"4/4_SOURCE_PROJECT_ONLY",Timebase:"480_MIDI_TICKS_PER_QUARTER_EXACT_RATIONAL",AudioVerification:"SYNTHETIC_SCORE_TIMEMAP_ONLY_AUDIO_WAVEFORM_NOT_CHECKED",Events:[]ScoreEvent{}}
 for _,e:=range ordered{
  seconds,err:=ExactSecondsAt(e.Tick,r.Tempo);if err!=nil{return ScoreTimeMap{},err}
  samples:=new(big.Rat).Mul(seconds,new(big.Rat).SetInt64(int64(p.Rate)))
  out.Events=append(out.Events,ScoreEvent{ChoreographyEvent:e,ExactSeconds:seconds.RatString(),ExactSamplePosition:samples.RatString(),EvidenceStatus:"ORIGINAL_SYNTHETIC_TIME_PROPOSAL_NO_MEASURED_MOTION"})
 }
 canonical,err:=json.Marshal(out);if err!=nil{return ScoreTimeMap{},err}
 sum:=sha256.Sum256(canonical)
 out.ContentID="sha256:"+hex.EncodeToString(sum[:])
 return out,nil
}
func FormatScoreRequest(p Project,tempo []TempoPoint,events []ChoreographyEvent)(ScoreRequest,error){
 hash,err:=PublicAudioHash(p);if err!=nil{return ScoreRequest{},err}
 if len(tempo)==0||len(events)==0{return ScoreRequest{},fmt.Errorf("missing events or tempo")}
 out:=ScoreRequest{Schema:AlignmentSchema,Origin:"ORIGINAL_SYNTHETIC",AudioProjectSHA256:hash,Tempo:tempo,Events:events}
 if err:=validRequest(p,out);err!=nil{return ScoreRequest{},err}
 return out,nil
}
func Capability()map[string]any {
 return map[string]any{"schema":AlignmentSchema,"available_actions":[]string{"plan-original-synthetic-score-time-map"},"audiences":[]string{"human-source-project-reader-existing","automation-go-api","agent-typed-capability"},"holds":[]string{"not-real-score-transcription","no-audio-waveform-timestamp-proof","no-physical-motion","no-private-character-input","not-product-ready"}}
}
// Keep an explicit difference between source-edited note project and a performed waveform.
func TimeMapIsNotPerformanceProof(o ScoreTimeMap)bool{
 return strings.Contains(o.AudioVerification,"NOT_CHECKED")
}
