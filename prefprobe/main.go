// prefprobe compares fixed ranking with pairwise Bradley-Terry on ORIGINAL
// synthetic feedback only. R016 private DLE #145 owns authenticated owner data.
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
 "math"
 "os"
 "regexp"
)

const version = "prefprobe.synthetic.v1"
var hashPattern = regexp.MustCompile("^[0-9a-f]{64}$")
var allowedReasons = map[string]bool{"lighting":true,"skin":true,"motion":true,"hair":true,"identity":true,"other":true}

type Feedback struct {
 Schema string `json:"schema"`
 EventID string `json:"event_id"`
 ScopeKind string `json:"scope_kind"`
 ScopeID string `json:"scope_id"`
 CharacterID string `json:"character_id"`
 SourceSHA256 string `json:"source_sha256"`
 LeftID string `json:"left_id"`
 RightID string `json:"right_id"`
 Choice string `json:"choice"`
 Reasons []string `json:"reasons"`
 SyntheticOnly bool `json:"synthetic_only"`
 Authority string `json:"authority"`
}

type Model struct {
 Scores map[string]map[string]float64
 Votes map[string]int
 PairVotes map[string]int
 Ingested map[string]string
 Accepted int
 Abstained int
}

func NewModel() *Model {return &Model{Scores:make(map[string]map[string]float64),Votes:make(map[string]int),PairVotes:make(map[string]int),Ingested:make(map[string]string)}}

func validate(f Feedback) error {
 if f.Schema!=version || !f.SyntheticOnly || f.Authority!="SYNTHETIC_FIXTURE_NOT_OWNER" {
  return errors.New("not source-admitted synthetic feedback")
 }
 if f.EventID=="" || len(f.EventID)>128 || f.ScopeID=="" || len(f.ScopeID)>128 ||
 f.CharacterID=="" || len(f.CharacterID)>128 || f.LeftID=="" || f.RightID=="" ||
 f.LeftID==f.RightID || f.LeftID==f.CharacterID || f.RightID==f.CharacterID ||
 len(f.LeftID)>128 || len(f.RightID)>128 || !hashPattern.MatchString(f.SourceSHA256) {
  return errors.New("unbound, conflicting or invalid feedback identity")
 }
 switch f.ScopeKind {case "project","character","shot": default: return errors.New("scope not recognized")}
 switch f.Choice {case "left","right","tie","neither","unsure": default: return errors.New("choice not recognized")}
 if len(f.Reasons)>6 {return errors.New("excessive reasons")}
 seen:=map[string]bool{}
 for _,reason:=range f.Reasons {
  if !allowedReasons[reason] || seen[reason] {return errors.New("invalid or duplicate reason")}
  seen[reason]=true
 }
 return nil
}

func scopeKey(f Feedback) string {
 // A JSON tuple avoids cross-scope aliases when IDs contain '/', 'source',
 // or other delimiter text. The key is internal, never a grant of authority.
 b,_:=json.Marshal([4]string{f.ScopeKind,f.ScopeID,f.CharacterID,f.SourceSHA256})
 return string(b)
}
func pairKey(f Feedback) string {
 a,b:=f.LeftID,f.RightID
 if b<a {a,b=b,a}
 encoded,_:=json.Marshal([6]string{f.ScopeKind,f.ScopeID,f.CharacterID,f.SourceSHA256,a,b})
 return string(encoded)
}
func (m *Model) Ingest(f Feedback) error {
 if err:=validate(f);err!=nil{return err}
 b,_:=json.Marshal(f)
 h:=sha256.Sum256(b)
 digest:=hex.EncodeToString(h[:])
 if prev,seen:=m.Ingested[f.EventID];seen {
  if prev!=digest{return errors.New("conflicting replay for event id")}
  return nil // same event is idempotent, not another vote
 }
 m.Ingested[f.EventID]=digest
 if f.Choice=="tie" || f.Choice=="neither" || f.Choice=="unsure" {
  m.Abstained++;return nil
 }
 k:=scopeKey(f)
 if m.Scores[k]==nil {m.Scores[k]=map[string]float64{}}
 left:=m.Scores[k][f.LeftID]
 right:=m.Scores[k][f.RightID]
 // L2 shrinkage keeps bounded, avoids unidentifiable drift in the 2-arm test.
 predicted:=1/(1+math.Exp(math.Max(-40,math.Min(40,right-left))))
 target:=0.0
 if f.Choice=="left" {target=1}
 update:=0.22*(target-predicted)
 m.Scores[k][f.LeftID]=math.Max(-6,math.Min(6,left+update-0.003*left))
 m.Scores[k][f.RightID]=math.Max(-6,math.Min(6,right-update-0.003*right))
 m.Votes[k]++
 m.PairVotes[pairKey(f)]++
 m.Accepted++
 return nil
}

func (m *Model) Rank(f Feedback) (string,string) {
 if err:=validate(f);err!=nil {return "ABSTAIN_INVALID_CONTEXT",""}
 k:=scopeKey(f)
 s,ok:=m.Scores[k]
 if !ok{return "ABSTAIN_NO_TRAINING",""}
 // Five is a predeclared synthetic safety gate, not a statistical confidence claim.
 if m.Votes[k]<5 || m.PairVotes[pairKey(f)]<5 {
  return "ABSTAIN_INSUFFICIENT_PAIR_EVIDENCE",""
 }
 a,hasA:=s[f.LeftID];b,hasB:=s[f.RightID]
 if !hasA || !hasB || math.Abs(a-b)<0.1 {return "ABSTAIN_UNCERTAIN",""}
 if a>b{return "SYNTHETIC_RANK_ONLY",f.LeftID}
 return "SYNTHETIC_RANK_ONLY",f.RightID
}

func walk(dec *json.Decoder) error {
 t,err:=dec.Token();if err!=nil{return err}
 d,ok:=t.(json.Delim);if !ok{return nil}
 switch d {
 case '{':
  keys:=map[string]bool{}
  for dec.More() {
   k,err:=dec.Token();if err!=nil{return err}
   key,ok:=k.(string);if !ok{return errors.New("invalid object key")}
   if keys[key]{return errors.New("duplicate JSON key")}
   keys[key]=true
   if err:=walk(dec);err!=nil{return err}
  }
  z,err:=dec.Token();if err!=nil || z!=json.Delim('}') {return errors.New("object close missing")}
 case '[':
  for dec.More() {if err:=walk(dec);err!=nil{return err}}
  z,err:=dec.Token();if err!=nil || z!=json.Delim(']') {return errors.New("array close missing")}
 default:return errors.New("unexpected JSON token")
 }
 return nil
}
func DecodeEvent(raw []byte) (Feedback,error) {
 var f Feedback
 if len(raw)==0||len(raw)>8192{return f,errors.New("invalid event size")}
 d:=json.NewDecoder(bytes.NewReader(raw))
 if err:=walk(d);err!=nil{return f,err}
 if _,err:=d.Token();err!=io.EOF{return f,errors.New("trailing JSON")}
 d=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 if err:=d.Decode(&f);err!=nil{return f,err}
 return f,validate(f)
}

func makeFixture(id string,n int, preferredLeft bool) Feedback {
 digest:=sha256.Sum256([]byte("ORIGINAL R037 synthetic material demo fixture"))
 choice:="right"
 if preferredLeft {choice="left"}
 return Feedback{Schema:version,EventID:fmt.Sprintf("%s-%02d",id,n),
  ScopeKind:"shot",ScopeID:id,CharacterID:"synthetic-bust",
  SourceSHA256:hex.EncodeToString(digest[:]),LeftID:"matte",RightID:"glossy",
  Choice:choice,Reasons:[]string{"lighting"},SyntheticOnly:true,
  Authority:"SYNTHETIC_FIXTURE_NOT_OWNER"}
}
type Report struct {
 Status string `json:"status"`
 Schema string `json:"schema"`
 TrainEvents int `json:"train_events"`
 HeldoutExamples int `json:"heldout_examples"`
 FixedCorrect int `json:"fixed_correct"`
 LearnedCorrect int `json:"learned_correct"`
 Abstentions int `json:"abstentions"`
 Qualifier string `json:"qualifier"`
}

func demo() (Report,error) {
 m:=NewModel()
 // Fixed baseline favors 'glossy'; synthetic scene label favors 'matte'.
 // Alternating display order prevents learning a fixed left-side preference.
 for i:=0;i<12;i++ {
  f:=makeFixture("original-shot",i,true)
  if i%2==1 {f.LeftID,f.RightID=f.RightID,f.LeftID;f.Choice="right"}
  if err:=m.Ingest(f);err!=nil{return Report{},err}
 }
 correct:=0;fixedCorrect:=0;abstain:=0
 for i:=12;i<16;i++ {
  f:=makeFixture("original-shot",i,true)
  if i%2==1 {f.LeftID,f.RightID=f.RightID,f.LeftID;f.Choice="right"}
  // The fixed baseline always predicts glossy; measure rather than invent its score.
  syntheticChoice:="matte"
  if f.Choice=="left" && f.LeftID=="glossy" || f.Choice=="right" && f.RightID=="glossy" {syntheticChoice="glossy"}
  if syntheticChoice=="glossy" {fixedCorrect++}
  status,best:=m.Rank(f)
  if status!="SYNTHETIC_RANK_ONLY" {abstain++} else if best=="matte" {correct++}
 }
 return Report{Status:"PASS_SYNTHETIC_RANKING_CONTRACT_ONLY",Schema:version,
  TrainEvents:m.Accepted,HeldoutExamples:4,FixedCorrect:fixedCorrect,LearnedCorrect:correct,
  Abstentions:abstain,Qualifier:"NOT_OWNER_FEEDBACK_OR_REAL_PHOTOREALISM_EVIDENCE"},nil
}
func main() {
 synthetic:=flag.Bool("synthetic",false,"run only original synthetic data")
 flag.Parse()
 if !*synthetic || flag.NArg()!=0 {fmt.Fprintln(os.Stderr,"HOLD: synthetic-only CLI");os.Exit(2)}
 r,err:=demo()
 if err!=nil {fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 // Sortable stable JSON record with no real user or protected asset data.
 out,_:=json.MarshalIndent(r,"","  ")
 fmt.Println(string(out))
 if r.LearnedCorrect!=4 || r.Abstentions!=0 {os.Exit(1)}
}
