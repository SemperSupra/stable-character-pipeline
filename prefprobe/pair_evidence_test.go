package main

import (
 "testing"
)

// Every event here is synthetic. Evidence count is for an exact candidate pair,
// not the whole shot, and gives no authority to learn real owner preferences.
func TestOnePairVoteCannotBorrowFourOtherPairVotes(t *testing.T) {
 m:=NewModel()
 target:=makeFixture("pair-scope",0,true)
 if err:=m.Ingest(target);err!=nil{t.Fatal(err)}
 for i:=1;i<=4;i++ {
  other:=makeFixture("pair-scope",i,true)
  other.LeftID="satin"
  other.RightID="velvet"
  if err:=m.Ingest(other);err!=nil{t.Fatal(err)}
 }
 if m.Votes[scopeKey(target)]!=5 || m.PairVotes[pairKey(target)]!=1 {
  t.Fatalf("preconditions invalid, all=%d pair=%d",
   m.Votes[scopeKey(target)],m.PairVotes[pairKey(target)])
 }
 status,choice:=m.Rank(target)
 if status!="ABSTAIN_INSUFFICIENT_PAIR_EVIDENCE" || choice!="" {
  t.Fatalf("unrelated pair choices unlawfully promoted target: %s %s",status,choice)
 }
 for i:=5;i<9;i++ {
  same:=makeFixture("pair-scope",i,true)
  if err:=m.Ingest(same);err!=nil{t.Fatal(err)}
 }
 status,choice=m.Rank(target)
 if status!="SYNTHETIC_RANK_ONLY" || choice!="matte" {
  t.Fatalf("five synthetic target votes still not qualified: %s %s",status,choice)
 }
}

func TestReversedCandidatePositionSharesExactPairEvidence(t *testing.T) {
 m:=NewModel()
 for i:=0;i<5;i++ {
  f:=makeFixture("balanced-pair",i,true)
  if i%2==1 {
   f.LeftID,f.RightID=f.RightID,f.LeftID
   f.Choice="right"
  }
  if err:=m.Ingest(f);err!=nil{t.Fatal(err)}
 }
 query:=makeFixture("balanced-pair",100,true)
 inverted:=query
 inverted.LeftID,inverted.RightID=inverted.RightID,inverted.LeftID
 if pairKey(query)!=pairKey(inverted) {t.Fatal("blinded display order changed pair identity")}
 s,a:=m.Rank(query)
 s2,b:=m.Rank(inverted)
 if s!="SYNTHETIC_RANK_ONLY" || s2!="SYNTHETIC_RANK_ONLY" || a!="matte" || b!="matte" {
  t.Fatalf("blinded A/B view bias %s/%s %s/%s",s,a,s2,b)
 }
}

func TestDelimitedCharacterAndShotIDsCannotAliasSourceScope(t *testing.T) {
 m:=NewModel()
 f:=makeFixture("alpha/character/beta",1,true)
 f.CharacterID="gamma"
 alternate:=f
 alternate.ScopeID="alpha"
 alternate.CharacterID="beta/character/gamma"
 if scopeKey(f)==scopeKey(alternate) {
  t.Fatal("typed scope collided despite distinct shot and character identities")
 }
 for i:=0;i<8;i++ {
  x:=f
  x.EventID="colliding-"+string(rune('A'+i))
  if err:=m.Ingest(x);err!=nil{t.Fatal(err)}
 }
 status,choice:=m.Rank(alternate)
 if status!="ABSTAIN_NO_TRAINING" || choice!="" {
  t.Fatalf("delimiter alias caused cross-character preference transfer %s %s",status,choice)
 }
}

func TestReplayAbstentionNeverIncrementsPairCounts(t *testing.T) {
 m:=NewModel()
 f:=makeFixture("pair-replay",1,true)
 for i:=0;i<100;i++ {
  if err:=m.Ingest(f);err!=nil{t.Fatal(err)}
 }
 if m.PairVotes[pairKey(f)]!=1 {t.Fatal("100 replays counted as pair evidence")}
 for i:=2;i<100;i++ {
  a:=makeFixture("pair-replay",i,true)
  a.Choice="unsure"
  if err:=m.Ingest(a);err!=nil{t.Fatal(err)}
 }
 if m.PairVotes[pairKey(f)]!=1 {t.Fatal("abstention counted as pair evidence")}
 status,choice:=m.Rank(f)
 if status!="ABSTAIN_INSUFFICIENT_PAIR_EVIDENCE" || choice!="" {
  t.Fatalf("unsafe synthetic preference from replay/abstentions %s %s",status,choice)
 }
}
