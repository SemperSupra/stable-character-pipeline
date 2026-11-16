package main

import (
 "fmt"
 "testing"
)

// All judgments below are INVENTED for original, public-safe synthetic data.
// A pass is an internal method control, never actual owner preference learning.

func syntheticVote(shot string,i int,winner string) Feedback {
 f:=makeFixture(shot,i,true)
 if i%2==1 {
  f.LeftID,f.RightID=f.RightID,f.LeftID
 }
 selected:=winner
 if i%11==0 {
  if selected=="matte" {selected="glossy"} else {selected="matte"}
 }
 f.Choice="right"
 if f.LeftID==selected {f.Choice="left"}
 return f
}

func TestOppositeContextPreferencesWithBlindSidesAndNoisyLabels(t *testing.T) {
 m:=NewModel()
 const training=40
 for i:=0;i<training;i++ {
  for _,want:=range []struct{scope,winner string}{
   {"lighting-soft-synthetic","matte"},
   {"lighting-hard-synthetic","glossy"},
  } {
   f:=syntheticVote(want.scope,i,want.winner)
   if err:=m.Ingest(f);err!=nil{t.Fatal(err)}
  }
 }
 for _,want:=range []struct{scope,winner string}{
  {"lighting-soft-synthetic","matte"},
  {"lighting-hard-synthetic","glossy"},
 } {
  correct:=0
  for i:=training;i<training+12;i++ {
   f:=syntheticVote(want.scope,i,want.winner)
   status,got:=m.Rank(f)
   if status!="SYNTHETIC_RANK_ONLY" {t.Fatalf("abstained on trained synthetic context %s: %s",want.scope,status)}
   if got==want.winner {correct++}
  }
  if correct!=12 {t.Fatalf("synthetic opposed-scope heldout failed: %s %d/12",want.scope,correct)}
  t.Logf("SYNTHETIC_NOISY_HOLDOUT context=%s recognized_preference=%s 12/12 (NOT OWNER)",want.scope,want.winner)
 }
 for _,mutate:=range []func(*Feedback){
  func(f *Feedback){f.ScopeID="new-lighting"},
  func(f *Feedback){f.CharacterID="not-the-same-person"},
  func(f *Feedback){f.SourceSHA256="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"},
 } {
  probe:=syntheticVote("lighting-soft-synthetic",100,"matte")
  mutate(&probe)
  status,selected:=m.Rank(probe)
  if status!="ABSTAIN_NO_TRAINING" || selected!="" {
   t.Fatalf("cross-context positive preference leaked %q %q",status,selected)
  }
 }
}

func TestConflictedSyntheticChoicesAbstain(t *testing.T) {
 m:=NewModel()
 for i:=0;i<8;i++ {
  f:=makeFixture("indifferent-shot",i,true)
  if i%2==1 {f.Choice="right"}
  if err:=m.Ingest(f);err!=nil{t.Fatal(err)}
 }
 status,selected:=m.Rank(makeFixture("indifferent-shot",88,true))
 if status!="ABSTAIN_UNCERTAIN" || selected!="" {
  t.Fatalf("conflicted evidence resulted in preference %s %s",status,selected)
 }
}

func TestReplayedSingleVoteCannotMeetMinimum(t *testing.T) {
 m:=NewModel();e:=makeFixture("replay-shot",1,true)
 for i:=0;i<100;i++ {
  if err:=m.Ingest(e);err!=nil {t.Fatal(err)}
 }
 status,selected:=m.Rank(e)
 if status!="ABSTAIN_INSUFFICIENT_EVIDENCE" || selected!="" || m.Votes[scopeKey(e)]!=1 {
  t.Fatalf("single repeated event counted as independent authority: %s %s",status,selected)
 }
}

func TestTieNeitherAndUnsureCannotMeetMinimum(t *testing.T) {
 m:=NewModel()
 for i:=0;i<100;i++ {
  f:=makeFixture("abstain-only",i,true)
  options:=[]string{"tie","neither","unsure"}
  f.Choice=options[i%3]
  if err:=m.Ingest(f);err!=nil {t.Fatal(err)}
 }
 f:=makeFixture("abstain-only",900,true)
 status,_:=m.Rank(f)
 if status!="ABSTAIN_NO_TRAINING" || m.Accepted!=0 || m.Abstained!=100 {
  t.Fatalf("abstention events changed ranking gate %s, %d accepted",status,m.Accepted)
 }
}

func TestFourVotesStillAbstainAndFifthCanBeMeasured(t *testing.T) {
 m:=NewModel()
 for i:=0;i<4;i++ {
  f:=makeFixture("minimum-evidence",i,true)
  if err:=m.Ingest(f);err!=nil {t.Fatal(err)}
 }
 probe:=makeFixture("minimum-evidence",100,true)
 status,selected:=m.Rank(probe)
 if status!="ABSTAIN_INSUFFICIENT_EVIDENCE" || selected!="" {
  t.Fatalf("four votes improperly sufficient: %s %s",status,selected)
 }
 if err:=m.Ingest(makeFixture("minimum-evidence",4,true));err!=nil {t.Fatal(err)}
 status,selected=m.Rank(probe)
 if status!="SYNTHETIC_RANK_ONLY" || selected!="matte" {
  t.Fatalf("five synthetic votes not measured: %s %s",status,selected)
 }
}

func TestEventIDReuseAcrossContextsIsConflictingReplay(t *testing.T) {
 m:=NewModel()
 a:=makeFixture("one",1,true)
 b:=makeFixture("two",1,true)
 a.EventID="single-id";b.EventID=a.EventID
 if err:=m.Ingest(a);err!=nil {t.Fatal(err)}
 if err:=m.Ingest(b);err==nil {t.Fatal("reused event ID across different contexts treated as two votes")}
 if m.Accepted!=1 {t.Fatal(fmt.Sprintf("accepted=%d expected=1",m.Accepted))}
}
