package main

import (
 "bytes"
 "encoding/json"
 "testing"
)

func TestSyntheticChoiceLearningAndBlindPosition(t *testing.T) {
 report,err:=demo()
 if err!=nil {t.Fatal(err)}
 if report.LearnedCorrect!=4||report.FixedCorrect!=0||report.HeldoutExamples!=4||
 report.Status!="PASS_SYNTHETIC_RANKING_CONTRACT_ONLY" {
  t.Fatalf("missing paired synthetic gain or wrong status: %+v",report)
 }
}

func TestIdempotentEventAndConflictingReplay(t *testing.T){
 m:=NewModel()
 e:=makeFixture("synthetic",1,true)
 if err:=m.Ingest(e);err!=nil{t.Fatal(err)}
 original:=m.Scores[scopeKey(e)]["matte"]
 if err:=m.Ingest(e);err!=nil{t.Fatal(err)}
 if m.Accepted!=1 || original!=m.Scores[scopeKey(e)]["matte"] {t.Fatal("duplicate synthetic feedback counted twice")}
 e.Choice="right"
 if err:=m.Ingest(e);err==nil{t.Fatal("conflicting event ID accepted")}
}

func TestScopeAndCharacterIsolation(t *testing.T) {
 m:=NewModel();e:=makeFixture("one-shot",1,true)
 for i:=1;i<=12;i++ {
  e.EventID="unique-"+string(rune('A'+i))
  if err:=m.Ingest(e);err!=nil{t.Fatal(err)}
 }
 _,winner:=m.Rank(e)
 if winner!="matte" {t.Fatal("training did not produce synthetic winner")}
 for _,modify:=range []func(*Feedback){
  func(v *Feedback){v.ScopeID="another-shot"},
  func(v *Feedback){v.CharacterID="synthetic-other"},
  func(v *Feedback){v.ScopeKind="project"},
  func(v *Feedback){v.SourceSHA256="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
 } {
  probe:=e;modify(&probe)
  status,_:=m.Rank(probe);if status!="ABSTAIN_NO_TRAINING"{t.Fatalf("scope leakage: %s",status)}
 }
}

func TestRejectNonSyntheticAuthorityAndBadChoices(t *testing.T) {
 var cases=[]func(*Feedback){
  func(f *Feedback){f.SyntheticOnly=false},
  func(f *Feedback){f.Authority="REAL_USER"},
  func(f *Feedback){f.Schema="next-version"},
  func(f *Feedback){f.LeftID=f.RightID},
  func(f *Feedback){f.SourceSHA256="mismatched"},
  func(f *Feedback){f.Choice="canonical"},
  func(f *Feedback){f.ScopeKind="global-private"},
  func(f *Feedback){f.Reasons=[]string{"identity","identity"}},
  func(f *Feedback){f.Reasons=[]string{"secret-biography"}},
 }
 for i,change:=range cases {
  f:=makeFixture("synthetic",i,true);change(&f)
  if err:=NewModel().Ingest(f);err==nil{t.Fatalf("accepted inadmissible case %d",i)}
 }
}

func TestTieNeitherUnsureAbstain(t *testing.T) {
 m:=NewModel()
 for i,choice:=range []string{"tie","neither","unsure"} {
  f:=makeFixture("synthetic",i,true);f.Choice=choice
  if err:=m.Ingest(f);err!=nil{t.Fatal(err)}
 }
 if m.Accepted!=0||m.Abstained!=3 {t.Fatalf("abstain counted as vote %+v",m)}
 status,_:=m.Rank(makeFixture("synthetic",4,true))
 if status!="ABSTAIN_NO_TRAINING" {t.Fatalf("unexpected policy: %s",status)}
}

func TestStrictJSONNoDuplicateKeysUnknownOrTrailing(t *testing.T) {
 f:=makeFixture("synthetic",1,true)
 b,err:=json.Marshal(f);if err!=nil{t.Fatal(err)}
 got,err:=DecodeEvent(b);if err!=nil||got.EventID!=f.EventID{t.Fatalf("valid event rejected: %v",err)}
 for _,bad:=range [][]byte{
  bytes.Replace(b,[]byte(`"choice":"left"`),[]byte(`"choice":"left","choice":"right"`),1),
  append(append([]byte{},b...),[]byte(`{} `)...),
  bytes.Replace(b,[]byte(`"synthetic_only":true`),[]byte(`"synthetic_only":false`),1),
  bytes.Replace(b,[]byte(`"authority":"SYNTHETIC_FIXTURE_NOT_OWNER"`),[]byte(`"authority":"OWNER"`),1),
 } {
  if _,err:=DecodeEvent(bad);err==nil{t.Fatalf("unsafe raw JSON accepted: %s",bad)}
 }
}

func TestRankingUncertaintyAndNoCanonicalizer(t *testing.T) {
 m:=NewModel();f:=makeFixture("synthetic",3,true)
 status,winner:=m.Rank(f)
 if status!="ABSTAIN_NO_TRAINING" || winner!="" {t.Fatal("untrained synthetic preference promoted")}
 if err:=m.Ingest(f);err!=nil{t.Fatal(err)}
 status,winner=m.Rank(f)
 if status!="ABSTAIN_INSUFFICIENT_EVIDENCE" || winner!="" {
  t.Fatalf("unsafe one-vote synthetic promotion %s %s",status,winner)
 }
 for i:=0;i<4;i++ {
  f.EventID="evidence-"+string(rune('A'+i))
  if err:=m.Ingest(f);err!=nil{t.Fatal(err)}
 }
 status,winner=m.Rank(f)
 if status!="SYNTHETIC_RANK_ONLY" || winner!="matte" {t.Fatalf("invalid narrow ranking %s %s",status,winner)}
}
