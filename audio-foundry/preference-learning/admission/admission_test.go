package admission
import (
 "crypto/sha256"
 "fmt"
 "strings"
 "testing"
)
func TestStrictPublicIntent(t *testing.T){
 ref:=strings.Repeat("a",64)
 payload:=[]byte(fmt.Sprintf(`{"schema":"audio.intent.v0","intent_id":"synthetic-a","revision":1,"classification":"%s","target_kind":"vocalization","description":"original synthetic vowel","reference_examples":[{"role":"positive","artifact_sha256":"%s","classification":"%s","rights_receipt_ref":"reviewed-synthetic-1"}]}`,Public,ref,Public))
 sha:=fmt.Sprintf("%x",sha256.Sum256(payload))
 m:=Manifest{AllowedPayloadSHA256:map[string]bool{sha:true},AllowedReferenceSHA256:map[string]bool{ref:true}}
 if got,e:=AdmitPublicIntent(payload,m);e!=nil||got!=sha{t.Fatalf("approved synthetic rejected: %v",e)}
 if _,e:=AdmitPublicIntent(payload,Manifest{});e==nil{t.Fatal("unapproved bytes passed")}
 if _,e:=AdmitPublicIntent(payload,Manifest{AllowedPayloadSHA256:m.AllowedPayloadSHA256});e==nil{t.Fatal("unapproved reference passed")}
}
func TestProtectedAndTrickyInputs(t *testing.T){
 ref:=strings.Repeat("a",64)
 for i,s:=range []string{
  `{"schema":"audio.preference_event.v0","classification":"PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL","description":"user choices"}`,
  `{"schema":"audio.intent.v0","classification":"PRIVATE_FINAL_CHARACTER_VOICE","description":"protected"}`,
  `{"schema":"audio.intent.v0","classification":"PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL","classification":"PRIVATE_FINAL_CHARACTER_VOICE","description":"duplicate"}`,
  `{"schema":"audio.intent.v0","classification":"PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL","description":"ok"} extra`,
  fmt.Sprintf(`{"schema":"audio.intent.v0","classification":"%s","description":"ok","reference_examples":[{"artifact_sha256":"%s","classification":"PRIVATE_FINAL_CHARACTER_VOICE","rights_receipt_ref":"r"}]}`,Public,ref),
 } {
  b:=[]byte(s);sha:=fmt.Sprintf("%x",sha256.Sum256(b));m:=Manifest{AllowedPayloadSHA256:map[string]bool{sha:true},AllowedReferenceSHA256:map[string]bool{ref:true}}
  if _,e:=AdmitPublicIntent(b,m);e==nil{t.Fatalf("negative case %d accepted",i)}
 }
}
