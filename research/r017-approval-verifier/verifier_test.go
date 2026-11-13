package verifier

import (
 "crypto/ed25519"
 "crypto/sha256"
 "testing"
 "time"
)
func fixture(t *testing.T)(Signed,Expectation,Trust,ed25519.PrivateKey){
 t.Helper()
 seed:=sha256.Sum256([]byte("public-synthetic-test-key-not-for-real-use"))
 priv:=ed25519.NewKeyFromSeed(seed[:]);pub:=priv.Public().(ed25519.PublicKey)
 now:=time.Unix(1800000000,0)
 r:=Receipt{Schema:"suprahuman-owner-selection-v1",Issuer:"test-owner",CandidateID:"synthetic-adult-1",PackRevision:"r3",EvidenceSHA256:SyntheticDigest(),Scope:"candidate-review",Nonce:"test-nonce-001",IssuedUnix:now.Unix()-60,ExpiresUnix:now.Unix()+60}
 signed,err:=signFixture(r,priv);if err!=nil{t.Fatal(err)}
 e:=Expectation{CandidateID:r.CandidateID,PackRevision:r.PackRevision,EvidenceSHA256:r.EvidenceSHA256,Scope:r.Scope,Now:now,MaxClockSkew:time.Second}
 trust:=Trust{Keys:map[string]ed25519.PublicKey{r.Issuer:pub},NonceSeen:map[string]bool{},Revoked:map[string]bool{}}
 return signed,e,trust,priv
}
func TestTrustBoundary(t *testing.T) {
 cases:=[]struct{name string;mutate func(*Signed,*Expectation,*Trust,ed25519.PrivateKey);want Status}{
 {"valid_synthetic_signature_for_review_only",func(*Signed,*Expectation,*Trust,ed25519.PrivateKey){},VerifiedForHumanReview},
 {"tampered_candidate",func(s *Signed,_ *Expectation,_ *Trust,_ ed25519.PrivateKey){s.Receipt.CandidateID="other"},Reject},
 {"cross_revision",func(_ *Signed,e *Expectation,_ *Trust,_ ed25519.PrivateKey){e.PackRevision="r4"},Reject},
 {"cross_evidence",func(_ *Signed,e *Expectation,_ *Trust,_ ed25519.PrivateKey){e.EvidenceSHA256="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},Reject},
 {"cross_scope",func(_ *Signed,e *Expectation,_ *Trust,_ ed25519.PrivateKey){e.Scope="canonical-write"},Reject},
 {"bad_signature",func(s *Signed,_ *Expectation,_ *Trust,_ ed25519.PrivateKey){s.Signature[0]^=1},Reject},
 {"not_yet_valid",func(_ *Signed,e *Expectation,_ *Trust,_ ed25519.PrivateKey){e.Now=e.Now.Add(-time.Hour)},Reject},
 {"expired",func(_ *Signed,e *Expectation,_ *Trust,_ ed25519.PrivateKey){e.Now=e.Now.Add(time.Hour)},Reject},
 {"revoked",func(s *Signed,_ *Expectation,t *Trust,_ ed25519.PrivateKey){t.Revoked[s.Receipt.Issuer+":"+s.Receipt.Nonce]=true},Reject},
 {"replayed",func(s *Signed,_ *Expectation,t *Trust,_ ed25519.PrivateKey){t.NonceSeen[s.Receipt.Issuer+":"+s.Receipt.Nonce]=true},Reject},
 {"unknown_issuer",func(_ *Signed,_ *Expectation,t *Trust,_ ed25519.PrivateKey){t.Keys=map[string]ed25519.PublicKey{}},Unknown},
 {"unavailable_replay_store",func(_ *Signed,_ *Expectation,t *Trust,_ ed25519.PrivateKey){t.NonceSeen=nil},Unknown},
 {"unavailable_revocation_store",func(_ *Signed,_ *Expectation,t *Trust,_ ed25519.PrivateKey){t.Revoked=nil},Unknown},
 {"absent_trusted_clock",func(_ *Signed,e *Expectation,_ *Trust,_ ed25519.PrivateKey){e.Now=time.Time{}},Unknown},
 {"invalid_digest",func(s *Signed,_ *Expectation,_ *Trust,_ ed25519.PrivateKey){s.Receipt.EvidenceSHA256="not-a-hash"},Reject},
 {"fake_claimed_issuer_signed_with_other_key",func(s *Signed,_ *Expectation,_ *Trust,_ ed25519.PrivateKey){seed:=sha256.Sum256([]byte("untrusted-actor"));other:=ed25519.NewKeyFromSeed(seed[:]);signed,_:=signFixture(s.Receipt,other);*s=signed},Reject},
 {"oversized_lifetime",func(s *Signed,_ *Expectation,_ *Trust,k ed25519.PrivateKey){s.Receipt.ExpiresUnix=s.Receipt.IssuedUnix+86401;*s,_=signFixture(s.Receipt,k)},Reject},
 {"missing_signature",func(s *Signed,_ *Expectation,_ *Trust,_ ed25519.PrivateKey){s.Signature=nil},Reject},
 }
 for _,tc:=range cases {t.Run(tc.name,func(t *testing.T){s,e,tr,k:=fixture(t);tc.mutate(&s,&e,&tr,k);got:=Verify(s,e,tr);if got.Status!=tc.want{t.Fatalf("got %+v want %s",got,tc.want)}})}
}
