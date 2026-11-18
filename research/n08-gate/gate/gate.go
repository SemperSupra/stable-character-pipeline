// Package gate provides a bounded, *research-only* compare-and-swap evidence state machine.
// A bound technical receipt NEVER implies owner acceptance, rights, or release.
package gate

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "sync"
)

type Stage string
const (
 Empty Stage = "EMPTY"
 SourcePinned Stage = "SOURCE_PINNED"
 Candidate Stage = "CANDIDATE"
 ReceiptBound Stage = "RECEIPT_BOUND"
 Hold Stage = "HOLD"
)
type State struct {
 Revision uint64 `json:"revision"`
 Stage Stage `json:"stage"`
 SourceSHA string `json:"source_sha256,omitempty"`
 ArtifactSHA string `json:"artifact_sha256,omitempty"`
 ReceiptSHA string `json:"receipt_sha256,omitempty"`
 Canonical bool `json:"canonical"`
 OwnerAccepted bool `json:"owner_accepted"`
 ReleaseAuthorized bool `json:"release_authorized"`
}
type Command struct {
 Kind string
 ExpectedRevision uint64
 SourceBytes []byte
 ExpectedSourceSHA string
 ArtifactBytes []byte
 ExpectedArtifactSHA string
 ReceiptBytes []byte
 ExpectedReceiptSHA string
}
type Receipt struct {
 Schema string `json:"schema"`
 SourceSHA string `json:"source_sha256"`
 ArtifactSHA string `json:"artifact_sha256"`
 Verdict string `json:"verdict"`
 OracleID string `json:"oracle_id"`
}
type Store struct {
 mu sync.Mutex
 state State
}
func NewStore() *Store { return &Store{state:State{Stage:Empty}} }
func (s *Store) Snapshot() State {
 s.mu.Lock()
 defer s.mu.Unlock()
 return s.state
}
func digest(data []byte) string {
 d:=sha256.Sum256(data)
 return hex.EncodeToString(d[:])
}
func wellFormedSHA(s string) bool {
 if len(s)!=64 { return false }
 for _,c:=range s { if !((c>='0' && c<='9') || (c>='a' && c<='f')) {return false} }
 return true
}
func duplicateSafeReceipt(raw []byte) (Receipt,error) {
 var receipt Receipt
 if len(raw)==0 || len(raw)>65536 {return receipt,errors.New("RECEIPT_SIZE")}
 dec:=json.NewDecoder(bytes.NewReader(raw))
 token,e:=dec.Token()
 if e!=nil || token!=json.Delim('{') {return receipt,errors.New("RECEIPT_OBJECT_REQUIRED")}
 seen:=make(map[string]bool)
 allowed:=map[string]bool{"schema":true,"source_sha256":true,"artifact_sha256":true,"verdict":true,"oracle_id":true}
 for dec.More() {
  tok,e:=dec.Token();if e!=nil{return receipt,errors.New("INVALID_RECEIPT_KEY")}
  key,ok:=tok.(string);if !ok || seen[key] || !allowed[key] {return receipt,errors.New("DUPLICATE_OR_UNEXPECTED_RECEIPT_KEY")}
  seen[key]=true
  var v json.RawMessage
  if e=dec.Decode(&v);e!=nil{return receipt,errors.New("INVALID_RECEIPT_VALUE")}
 }
 token,e=dec.Token()
 if e!=nil || token!=json.Delim('}') {return receipt,errors.New("INVALID_RECEIPT_CLOSE")}
 if _,e=dec.Token();e!=io.EOF{return receipt,errors.New("RECEIPT_TRAILING_DATA")}
 d:=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 if e=d.Decode(&receipt);e!=nil{return receipt,e}
 if len(seen)!=len(allowed) || receipt.Schema!="scp.n08.synthetic-receipt.v1" ||
  !wellFormedSHA(receipt.SourceSHA) || !wellFormedSHA(receipt.ArtifactSHA) ||
  receipt.Verdict!="PASS_NARROW" || receipt.OracleID!="independent-synthetic-reference-v1" {
  return receipt,errors.New("RECEIPT_UNSUPPORTED_OR_INCOMPLETE")
 }
 return receipt,nil
}
// Apply is atomic for cooperating callers only. It does not implement filesystem CAS.
// No transition may grant canonical status, owner acceptance or release authority.
func (s *Store) Apply(c Command) (State,error) {
 s.mu.Lock()
 defer s.mu.Unlock()
 prior:=s.state
 if c.ExpectedRevision!=prior.Revision {return prior,fmt.Errorf("STALE_REVISION expected=%d actual=%d",c.ExpectedRevision,prior.Revision)}
 next:=prior
 switch c.Kind {
 case "PIN_SOURCE":
  if prior.Stage!=Empty || len(c.SourceBytes)==0 || !wellFormedSHA(c.ExpectedSourceSHA) || digest(c.SourceBytes)!=c.ExpectedSourceSHA {
   return prior,errors.New("SOURCE_ADMISSION_REJECTED")
  }
  next.SourceSHA=c.ExpectedSourceSHA;next.Stage=SourcePinned
 case "DERIVE":
  if prior.Stage!=SourcePinned || prior.SourceSHA!=c.ExpectedSourceSHA || len(c.ArtifactBytes)==0 ||
   !wellFormedSHA(c.ExpectedArtifactSHA) || digest(c.ArtifactBytes)!=c.ExpectedArtifactSHA {
   return prior,errors.New("DERIVATION_LINEAGE_REJECTED")
  }
  next.ArtifactSHA=c.ExpectedArtifactSHA;next.Stage=Candidate
 case "BIND_RECEIPT":
  if prior.Stage!=Candidate || c.ExpectedSourceSHA!=prior.SourceSHA || c.ExpectedArtifactSHA!=prior.ArtifactSHA ||
    !wellFormedSHA(c.ExpectedReceiptSHA) || digest(c.ReceiptBytes)!=c.ExpectedReceiptSHA {
   return prior,errors.New("RECEIPT_LINEAGE_REJECTED")
  }
  receipt,e:=duplicateSafeReceipt(c.ReceiptBytes)
  if e!=nil{return prior,e}
  if receipt.SourceSHA!=prior.SourceSHA || receipt.ArtifactSHA!=prior.ArtifactSHA {
   return prior,errors.New("RECEIPT_SOURCE_OR_ARTIFACT_MISMATCH")
  }
  next.ReceiptSHA=c.ExpectedReceiptSHA;next.Stage=ReceiptBound
 case "HOLD":
  if prior.Stage==Empty || prior.Stage==Hold{return prior,errors.New("HOLD_NOT_APPLICABLE")}
  next.Stage=Hold
 case "OWNER_ACCEPT", "RELEASE":
  return prior,errors.New("EXTERNAL_OWNER_AND_RELEASE_AUTHORITY_REQUIRED")
 default:
  return prior,errors.New("UNKNOWN_TRANSITION")
 }
 next.Revision++
 s.state=next
 return next,nil
}
