package releasemodel

import (
 "strings"
 "testing"
 "github.com/sempersupra/stable-character-pipeline/releasegate"
 "github.com/sempersupra/stable-character-pipeline/releaseproof"
)

// Independent R16 state-transition and synthetic owner-flag review.
// This uses the production R0/R0b imports and real R0c Evaluate;
// it does not pretend that user-supplied owner booleans are authenticated grants.
func TestR16NoReleaseFromAnyUnauthenticatedOwnerMask(t *testing.T){
 for mask:=0;mask<32;mask++ {
  owner:=OwnerState{mask&1!=0,mask&2!=0,mask&4!=0,mask&8!=0,mask&16!=0}
  for _,phase:=range []string{"draft","candidate","released"}{
   m:=baseline();m.Phase=phase
   result:=Evaluate(m,releaseproof.TrustPolicy{},t.TempDir(),t.TempDir(),owner)
   if result.Status!="HOLD"{
    t.Fatalf("UNAUTHENTICATED_RELEASE_PROMOTION mask=%d phase=%s result=%+v",mask,phase,result)
   }
   if phase=="draft"&&result.Code!="DRAFT_UNPROMOTABLE"{
    t.Fatalf("DRAFT_EVIDENCE_CHANGED mask=%d result=%+v",mask,result)
   }
  }
 }
}
func TestR16FailureUnknownAndInventedEvidenceCannotAdvancePhase(t *testing.T){
 for _,phase:=range []string{"draft","candidate","released"}{
  for _,gate:=range releasegate.RequiredGates{
   for _,bad:=range []string{"FAIL","UNKNOWN"}{
    m:=baseline();m.Phase=phase
    m.Gates[gate]=releasegate.Evidence{Status:bad,ReceiptSHA:"sha256:"+strings.Repeat("c",64)}
    for mask:=0;mask<32;mask++{
     o:=OwnerState{mask&1!=0,mask&2!=0,mask&4!=0,mask&8!=0,mask&16!=0}
     result:=Evaluate(m,releaseproof.TrustPolicy{},t.TempDir(),t.TempDir(),o)
     if result.Status!="HOLD"{
      t.Fatalf("BAD_GATE_PROMOTED phase=%s gate=%s state=%s mask=%d result=%+v",phase,gate,bad,mask,result)
     }
    }
   }
  }
 }
}
func TestR16FakeRightsReviewCannotBypassOriginalProof(t *testing.T){
 m:=baseline()
 for _,gate:=range releasegate.RequiredGates{
  m.Gates[gate]=releasegate.Evidence{Status:"PASS",ReceiptSHA:"sha256:"+strings.Repeat("f",64)}
 }
 got:=Evaluate(m,releaseproof.TrustPolicy{},t.TempDir(),t.TempDir(),OwnerState{true,true,true,true,true})
 if got.Status!="HOLD"||got.Code!="INDEPENDENT_EVIDENCE_NOT_QUALIFIED"{
  t.Fatalf("ORIGINAL_PROOF_REQUIRED: %+v",got)
 }
}
