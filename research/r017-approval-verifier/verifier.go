package verifier

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "strings"
 "time"
)

// Receipt is an immutable assertion of owner intent, NOT a canonicalization command.
// All fields are bound to its Ed25519 signature using explicit domain separation.
type Receipt struct {
 Schema string `json:"schema"`
 Issuer string `json:"issuer"`
 CandidateID string `json:"candidate_id"`
 PackRevision string `json:"pack_revision"`
 EvidenceSHA256 string `json:"evidence_sha256"`
 Scope string `json:"scope"`
 Nonce string `json:"nonce"`
 IssuedUnix int64 `json:"issued_unix"`
 ExpiresUnix int64 `json:"expires_unix"`
}
type Signed struct { Receipt Receipt `json:"receipt"`; Signature []byte `json:"signature"` }
type Expectation struct {
 CandidateID string
 PackRevision string
 EvidenceSHA256 string
 Scope string
 Now time.Time
 MaxClockSkew time.Duration
}
type Status string
const (
 VerifiedForHumanReview Status = "VERIFIED_FOR_HUMAN_REVIEW_ONLY"
 Unknown Status = "UNKNOWN_ABSTAIN"
 Reject Status = "REJECT"
)
type Decision struct { Status Status; Reason string }
// Trust comes from product authority, never from the submitted receipt.
// NonceSeen and Revoked are immutable lookups, not atomic state transitions.
type Trust struct {
 Keys map[string]ed25519.PublicKey
 NonceSeen map[string]bool
 Revoked map[string]bool
}
func digestValid(s string) bool {
 if len(s)!=64 || strings.ToLower(s)!=s {return false}
 _,err:=hex.DecodeString(s);return err==nil
}
func payload(r Receipt) ([]byte,error) {
 b,err:=json.Marshal(r)
 if err!=nil{return nil,err}
 return append([]byte("suprahuman.owner-selection.v1\x00"),b...),nil
}
// Verify never writes or promotes any CharacterPack.
func Verify(s Signed, e Expectation, t Trust) Decision {
 reject:=func(reason string) Decision{return Decision{Reject,reason}}
 unknown:=func(reason string) Decision{return Decision{Unknown,reason}}
 r:=s.Receipt
 if r.Schema!="suprahuman-owner-selection-v1" || r.Issuer=="" || r.CandidateID=="" || r.PackRevision=="" || r.Scope=="" || r.Nonce=="" {return reject("invalid_identity_or_schema")}
 if r.Scope!="candidate-review" || e.Scope!="candidate-review" {return reject("scope_not_review_only")}
 if !digestValid(r.EvidenceSHA256) || !digestValid(e.EvidenceSHA256) {return reject("invalid_evidence_digest")}
 if r.CandidateID!=e.CandidateID || r.PackRevision!=e.PackRevision || r.EvidenceSHA256!=e.EvidenceSHA256 || r.Scope!=e.Scope {return reject("scope_revision_or_evidence_mismatch")}
 if r.IssuedUnix<=0 || r.ExpiresUnix<=r.IssuedUnix || r.ExpiresUnix-r.IssuedUnix>86400 {return reject("invalid_receipt_lifetime")}
 if e.Now.IsZero() || e.MaxClockSkew<0 || e.MaxClockSkew>5*time.Minute {return unknown("trusted_clock_unavailable")}
 now:=e.Now.Unix();skew:=int64(e.MaxClockSkew.Seconds())
 if now+skew<r.IssuedUnix || now-skew>=r.ExpiresUnix {return reject("expired_or_not_yet_valid")}
 key,ok:=t.Keys[r.Issuer];if !ok || len(key)!=ed25519.PublicKeySize {return unknown("issuer_key_not_admitted")}
 if t.Revoked==nil || t.NonceSeen==nil {return unknown("revocation_or_replay_store_unavailable")}
 if t.Revoked[r.Issuer+":"+r.Nonce] {return reject("revoked")}
 if t.NonceSeen[r.Issuer+":"+r.Nonce] {return reject("nonce_replayed")}
 p,err:=payload(r);if err!=nil {return unknown("payload_encoding_error")}
 if !ed25519.Verify(key,p,s.Signature) {return reject("invalid_signature")}
 return Decision{VerifiedForHumanReview,"signature_bound_to_requested_candidate"}
}
func signFixture(r Receipt,k ed25519.PrivateKey) (Signed,error) {
 if len(k)!=ed25519.PrivateKeySize{return Signed{},errors.New("bad private key")}
 p,err:=payload(r);if err!=nil{return Signed{},err}
 return Signed{r,ed25519.Sign(k,p)},nil
}
func SyntheticDigest() string {h:=sha256.Sum256([]byte("synthetic-only-no-character-assets"));return hex.EncodeToString(h[:])}
