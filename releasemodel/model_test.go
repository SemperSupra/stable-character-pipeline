package releasemodel
import (
 "strings"
 "testing"
 "github.com/sempersupra/stable-character-pipeline/releasegate"
 "github.com/sempersupra/stable-character-pipeline/releaseproof"
)
func baseline()releasegate.Manifest{
 m:=releasegate.Manifest{Schema:releasegate.Schema,Phase:"candidate",
   Scope:"public-synthetic",SourceSHA:strings.Repeat("a",40),
   ImageDigest:"sha256:"+strings.Repeat("b",64),Gates:map[string]releasegate.Evidence{}}
 for _,g:=range releasegate.RequiredGates{
  m.Gates[g]=releasegate.Evidence{Status:"PASS",ReceiptSHA:"sha256:"+strings.Repeat("c",64)}
 }
 return m
}
func TestExhaustiveNineGateStateSpace(t *testing.T){
 states:=[]string{"PASS","FAIL","UNKNOWN"}
 count,passed,drafted,held:=0,0,0,0
 for mask:=0;mask<19683;mask++{
  m:=baseline();number:=mask;allPass:=true
  for _,g:=range releasegate.RequiredGates{
   k:=number%3;number/=3
   if k!=0{allPass=false}
   m.Gates[g]=releasegate.Evidence{Status:states[k],ReceiptSHA:"sha256:"+strings.Repeat("c",64)}
  }
  for _,phase:=range []string{"draft","candidate","released"}{
   m.Phase=phase;got:=releasegate.Validate(m);count++
   if phase=="draft"{
    if got.Status!="UNKNOWN"{t.Fatalf("draft bypass mask=%d got=%+v",mask,got)}
    drafted++
   }else if allPass{
    if got.Status!="PASS"{t.Fatalf("structural contract changed mask=%d got=%+v",mask,got)}
    passed++
   }else{
    if got.Status!="FAIL"{t.Fatalf("unsafe promotion mask=%d phase=%s got=%+v",mask,phase,got)}
    held++
   }
  }
 }
 if count!=59049||passed!=2||drafted!=19683||held!=39364{
  t.Fatalf("states=%d pass=%d unknown=%d fail=%d",count,passed,drafted,held)
 }
 t.Logf("EXHAUSTIVE 59049: structural pass=2 draft unknown=19683 fail=39364")
}
func TestInventedHashesNeverYieldAuthenticatedRelease(t *testing.T){
 m:=baseline()
 if releasegate.Validate(m).Status!="PASS"{t.Fatal("structural fixture changed")}
 owner:=OwnerState{true,true,true,true,true}
 got:=Evaluate(m,releaseproof.TrustPolicy{},t.TempDir(),t.TempDir(),owner)
 if got.Status!="HOLD"||got.Code!="INDEPENDENT_EVIDENCE_NOT_QUALIFIED"{t.Fatal(got)}
}
func TestAll32OwnerGateCombinations(t *testing.T){
 for mask:=0;mask<32;mask++{
  o:=OwnerState{mask&1!=0,mask&2!=0,mask&4!=0,mask&8!=0,mask&16!=0}
  if o.All()!=(mask==31){t.Fatalf("owner boolean model false positive: %05b",mask)}
 }
}
func TestDraftNeverPromotedByFakeOwnerFlags(t *testing.T){
 m:=baseline();m.Phase="draft"
 got:=Evaluate(m,releaseproof.TrustPolicy{},t.TempDir(),t.TempDir(),OwnerState{true,true,true,true,true})
 if got.Status!="HOLD"||got.Code!="DRAFT_UNPROMOTABLE"{t.Fatal(got)}
}

func TestIntegratedR0bDeniesUndeclaredClaims(t *testing.T){
 m:=baseline()
 m.Gates["unauthenticated_extra"]=releasegate.Evidence{Status:"PASS",ReceiptSHA:"sha256:"+strings.Repeat("d",64)}
 if got:=releasegate.Validate(m);got.Status!="PASS"{t.Fatalf("unexpected structural baseline: %+v",got)}
 verified:=releaseproof.Verify(m,releaseproof.TrustPolicy{},t.TempDir(),t.TempDir())
 if verified.Code!="UNDECLARED_GATE"{t.Fatalf("stale or bypassed independent source: %+v",verified)}
}
