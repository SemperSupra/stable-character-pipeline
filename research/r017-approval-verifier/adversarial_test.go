package verifier

import "testing"

// Previously a fully signed request with both untrusted inputs set to
// canonical-write received VERIFIED_FOR_HUMAN_REVIEW_ONLY; keep this denied.
func TestRejectCallerSelectedCanonicalWriteScope(t *testing.T) {
 s,e,tr,k:=fixture(t)
 s.Receipt.Scope="canonical-write"
 e.Scope="canonical-write"
 var err error
 s,err=signFixture(s.Receipt,k)
 if err!=nil {t.Fatal(err)}
 got:=Verify(s,e,tr)
 if got.Status!=Reject || got.Reason!="scope_not_review_only" {t.Fatalf("expected REJECT scope_not_review_only, got %+v",got)}
}

// Demonstrates, but does not mask, the known snapshot-only nonce limitation.
// Both calls read an unchanged snapshot, hence both return the *review-only*
// result. Product authority must implement an atomic consume/write operation.
func TestSnapshotNonceIsNotTransactional(t *testing.T) {
 s,e,tr,_:=fixture(t)
 a,b:=Verify(s,e,tr),Verify(s,e,tr)
 if a.Status!=VerifiedForHumanReview || b.Status!=VerifiedForHumanReview {
  t.Fatalf("snapshot-only verifier contract changed: first=%+v second=%+v",a,b)
 }
}
