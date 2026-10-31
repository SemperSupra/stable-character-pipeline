package main

import "testing"

// Independent reviewer: the original SHA-pinned CLI is a separate boundary.
// These direct policy tests prohibit structurally valid but substituted actors.
func TestW9AReviewerRejectsDuplicateOriginalActorID(t *testing.T) {
 s,p:=fixture()
 s.Actors[1].ID=s.Actors[0].ID
 if err:=Validate(s,p);err==nil {
  t.Fatal("FIRST_RED_DUPLICATE_ACTOR_ACCEPTED: two source actor rows represent one actor")
 }
}
func TestW9AReviewerRejectsSubstitutedOriginalActorID(t *testing.T) {
 s,p:=fixture()
 s.Actors[1].ID="UnknownSynthetic"
 if err:=Validate(s,p);err==nil {
  t.Fatal("FIRST_RED_SUBSTITUTED_ACTOR_ACCEPTED: independent source actor identity not bound")
 }
}
func TestW9AReviewerOriginalTwoActorsRetainAbstention(t *testing.T) {
 s,p:=fixture()
 v,err:=Evaluate(s,p,"review-original-fixture")
 if err!=nil {t.Fatal(err)}
 if v.SourceGroundTruthIsNormativeOracle || v.HumanNaturalGait!="ABSTAIN_UNQUALIFIED_SOURCE_RIG" ||
  v.NormativeROM!="UNKNOWN_NO_APPROVED_INDIVIDUAL_LIMITS"{
  t.Fatalf("UNAUTHORIZED_BIOLOGICAL_PROMOTION: %+v",v)
 }
}
