package admission

import (
    "crypto/sha256"
    "fmt"
    "strings"
    "testing"
)

func TestAdmitRejectAmbiguousApprovedPayloads(t *testing.T) {
    good:=`{"schema":"audio.intent.v0","intent_id":"fixture-a","revision":1,"classification":"PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL","target_kind":"speech","description":"original synthetic only"}`
    negatives:=[]string{
        strings.Replace(good,`"intent_id":"fixture-a",`, "",1),
        strings.Replace(good,`"revision":1,`, "",1),
        strings.Replace(good,`"target_kind":"speech",`, "",1),
        strings.Replace(good,`"revision":1`, `"revision":"one"`,1),
        strings.Replace(good,`"target_kind":"speech"`, `"target_kind":"unknown"`,1),
        strings.Replace(good,`"intent_id":"fixture-a"`, `"intent_id":"../../oops"`,1),
        strings.Replace(good,`"description":"original synthetic only"`, `"description":"original synthetic only","extra_private_metadata":"secret"`,1),
        strings.Replace(good,`"description":"original synthetic only"`, `"description":"original synthetic only","language":"zz"`,1),
        strings.TrimSuffix(good,"}")+`,"reference_examples":[{"role":"positive","role":"negative","artifact_sha256":"`+strings.Repeat("a",64)+`","classification":"PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL","rights_receipt_ref":"fixture"}]}`,
        strings.TrimSuffix(good,"}")+`,"reference_examples":[{"role":"positive","artifact_sha256":"`+strings.Repeat("a",64)+`","classification":"PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL","rights_receipt_ref":"fixture","unknown_private_field":"secret"}]}`,
    }
    for i,s:=range append([]string{good},negatives...) {
        b:=[]byte(s);sha:=fmt.Sprintf("%x",sha256.Sum256(b))
        m:=Manifest{AllowedPayloadSHA256:map[string]bool{sha:true},AllowedReferenceSHA256:map[string]bool{strings.Repeat("a",64):true}}
        got,err:=AdmitPublicIntent(b,m)
        if i==0 {
            if err!=nil||got!=sha{t.Fatalf("valid reviewed synthetic denied: %v",err)}
        } else if err==nil {
            t.Fatalf("unsafe schema-shape case %d accepted",i)
        }
    }
}
func TestNestedDuplicateScanner(t *testing.T) {
    inputs:=[]string{`{"a":[{"b":1,"b":2}]}`,`{"outer":{"inner":{"x":"one","x":"two"}}}`,`{"a":1}{"b":2}`}
    for _,s:=range inputs {if err:=rejectNestedDuplicates([]byte(s));err==nil{t.Fatalf("accepted duplicate/trailing: %s",s)}}
    if err:=rejectNestedDuplicates([]byte(`{"outer":[{"x":1},{"x":2}],"ok":true}`));err!=nil{t.Fatal(err)}
}
