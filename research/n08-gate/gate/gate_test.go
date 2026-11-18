package gate
import (
 "bytes"
 "encoding/json"
 "strings"
 "sync"
 "sync/atomic"
 "testing"
)

func goodReceipt(sourceSHA, artifactSHA string) []byte {
 r:=Receipt{"scp.n08.synthetic-receipt.v1",sourceSHA,artifactSHA,"PASS_NARROW","independent-synthetic-reference-v1"}
 out,_:=json.Marshal(r)
 return out
}
func assertStage(t *testing.T,s State,expected Stage,rev uint64) {
 t.Helper()
 if s.Stage!=expected || s.Revision!=rev || s.Canonical || s.OwnerAccepted || s.ReleaseAuthorized {t.Fatalf("unexpected stage or authority: %+v",s)}
}
func setup(t *testing.T)(*Store,string,string,[]byte) {
 t.Helper()
 s:=NewStore()
 source:=[]byte("original synthetic character scene placeholder")
 artifact:=[]byte("original synthetic derived candidate")
 srcSHA,artSHA:=digest(source),digest(artifact)
 st,e:=s.Apply(Command{Kind:"PIN_SOURCE",ExpectedRevision:0,SourceBytes:source,ExpectedSourceSHA:srcSHA})
 if e!=nil{t.Fatal(e)}
 assertStage(t,st,SourcePinned,1)
 st,e=s.Apply(Command{Kind:"DERIVE",ExpectedRevision:1,ExpectedSourceSHA:srcSHA,ArtifactBytes:artifact,ExpectedArtifactSHA:artSHA})
 if e!=nil{t.Fatal(e)}
 assertStage(t,st,Candidate,2)
 return s,srcSHA,artSHA,goodReceipt(srcSHA,artSHA)
}
func TestHappyReceiptIsNeverAcceptance(t *testing.T) {
 s,source,artifact,receipt:=setup(t)
 st,e:=s.Apply(Command{Kind:"BIND_RECEIPT",ExpectedRevision:2,ExpectedSourceSHA:source,ExpectedArtifactSHA:artifact,ReceiptBytes:receipt,ExpectedReceiptSHA:digest(receipt)})
 if e!=nil{t.Fatal(e)}
 assertStage(t,st,ReceiptBound,3)
 for _,op:=range []string{"OWNER_ACCEPT","RELEASE"} {
  if _,e=s.Apply(Command{Kind:op,ExpectedRevision:3});e==nil{t.Fatalf("unsafe transition %s",op)}
 }
 assertStage(t,s.Snapshot(),ReceiptBound,3)
}
func TestStaleCASDoesNotMutate(t *testing.T) {
 s,_,_,_:=setup(t)
 if _,e:=s.Apply(Command{Kind:"HOLD",ExpectedRevision:1});e==nil{t.Fatal("stale accepted")}
 assertStage(t,s.Snapshot(),Candidate,2)
}
func TestReceiptMutationsRejected(t *testing.T) {
 s,src,art,r:=setup(t)
 cases:=[][]byte{
  []byte(`{"schema":"scp.n08.synthetic-receipt.v1","schema":"scp.n08.synthetic-receipt.v1"}`),
  []byte("[]"),
  []byte(string(r)+"{}"),
  bytes.Replace(r,[]byte(art),[]byte(digest([]byte("unrelated"))),1),
  bytes.Replace(r,[]byte(src),[]byte(digest([]byte("forged"))),1),
  bytes.Replace(r,[]byte("PASS_NARROW"),[]byte("PASS"),1),
  bytes.Replace(r,[]byte("independent-synthetic-reference-v1"),[]byte("owner-self-report"),1),
  []byte(`{"schema":"scp.n08.synthetic-receipt.v1","owner_approved":true}`),
 }
 for i,raw:=range cases {
  _,e:=s.Apply(Command{Kind:"BIND_RECEIPT",ExpectedRevision:2,ExpectedSourceSHA:src,ExpectedArtifactSHA:art,ReceiptBytes:raw,ExpectedReceiptSHA:digest(raw)})
  if e==nil{t.Fatalf("unsafe receipt %d",i)}
  assertStage(t,s.Snapshot(),Candidate,2)
 }
}
func TestSourceAndArtifactHashRequired(t *testing.T) {
 s:=NewStore()
 src:=[]byte("synthetic")
 if _,e:=s.Apply(Command{Kind:"PIN_SOURCE",ExpectedRevision:0,SourceBytes:src,ExpectedSourceSHA:strings.Repeat("0",64)});e==nil{t.Fatal("wrong hash admitted")}
 assertStage(t,s.Snapshot(),Empty,0)
 s2,source,_,_:=setup(t)
 if _,e:=s2.Apply(Command{Kind:"DERIVE",ExpectedRevision:2,ExpectedSourceSHA:source,ArtifactBytes:[]byte("other"),ExpectedArtifactSHA:strings.Repeat("0",64)});e==nil{t.Fatal("duplicate derivation")}
 assertStage(t,s2.Snapshot(),Candidate,2)
}
func TestConcurrentCASHasExactlyOneWinner(t *testing.T) {
 s,_,_,_:=setup(t)
 var success atomic.Int32
 var wg sync.WaitGroup
 for i:=0;i<50;i++ {
  wg.Add(1)
  go func() {
   defer wg.Done()
   if _,e:=s.Apply(Command{Kind:"HOLD",ExpectedRevision:2});e==nil{success.Add(1)}
  }()
 }
 wg.Wait()
 if n:=success.Load();n!=1{t.Fatalf("CAS winners=%d",n)}
 assertStage(t,s.Snapshot(),Hold,3)
}
func TestUnsupportedTransitionAndHold(t *testing.T) {
 s,_,_,_:=setup(t)
 if _,e:=s.Apply(Command{Kind:"PROMOTE",ExpectedRevision:2});e==nil{t.Fatal("unrecognized transition")}
 st,e:=s.Apply(Command{Kind:"HOLD",ExpectedRevision:2})
 if e!=nil{t.Fatal(e)}
 assertStage(t,st,Hold,3)
 if _,e=s.Apply(Command{Kind:"HOLD",ExpectedRevision:3});e==nil{t.Fatal("hold reapplication")}
}
