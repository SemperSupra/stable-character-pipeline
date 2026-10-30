// Package bridge vets source-neutral CPE/SearXNG handoff metadata.
// It deliberately neither compiles CPE concepts nor makes network calls.
package bridge

import (
 "crypto/sha256"
 "encoding/hex"
 "errors"
 "net/url"
 "strings"
 "unicode/utf8"
 "github.com/SemperSupra/stable-character-pipeline/research/providers/sweeps"
)
type Input struct {
 Schema string `json:"schema"`
 PlanRef string `json:"plan_ref"`
 AdapterSourceRef string `json:"adapter_source_ref"`
 CPEProjectionRef string `json:"cpe_projection_ref"`
 TargetID string `json:"target_id"`
 TargetOrigin string `json:"target_origin"`
 FormLanguage string `json:"form_language"`
 Term string `json:"term"`
 SourceEvidenceRef string `json:"source_evidence_ref"`
 Classification string `json:"classification"`
 DisclosureApprovalRef string `json:"disclosure_approval_ref,omitempty"`
 Operation string `json:"operation"`
}
type Receipt struct {
 Schema string `json:"schema"`
 Status string `json:"status"`
 PlanRef string `json:"plan_ref"`
 AdapterSourceRef string `json:"adapter_source_ref"`
 TargetID string `json:"target_id"`
 TermDigest string `json:"term_digest,omitempty"`
 FormLanguage string `json:"form_language"`
 OutboundCalls int `json:"outbound_calls"`
 ConceptAuthorityMutation bool `json:"concept_authority_mutation"`
 RawSearchTermPersisted bool `json:"raw_search_term_persisted"`
 Reason string `json:"reason"`
}
func Check(in Input, allowlistedOrigins map[string]bool) (Receipt,error){
 out:=Receipt{Schema:"scp.search_bridge_receipt.v1",Status:"HOLD",PlanRef:in.PlanRef,AdapterSourceRef:in.AdapterSourceRef,TargetID:in.TargetID,FormLanguage:in.FormLanguage,OutboundCalls:0,ConceptAuthorityMutation:false,RawSearchTermPersisted:false}
 fail:=func(s string)(Receipt,error){out.Reason=s;return out,errors.New(s)}
 if in.Schema!="scp.search_projection_handoff.v1"||in.PlanRef==""||in.AdapterSourceRef==""||in.CPEProjectionRef==""||in.SourceEvidenceRef=="" {return fail("missing exact source snapshot or proposal lineage")}
 if in.Operation!="search_only" {return fail("not a read-only search observation")}
 if in.TargetID==""||!allowlistedOrigins[in.TargetOrigin] {return fail("origin not pre-qualified in trusted catalog")}
 u,err:=url.Parse(in.TargetOrigin);if err!=nil||u.Scheme!="https"||u.Host==""||u.User!=nil||u.RawQuery!=""||u.Fragment!=""||u.Path!="" {return fail("bad origin / URL disclosure boundary")}
 if !sweeps.ValidLanguage(in.FormLanguage)||!utf8.ValidString(in.Term)||in.Term==""||len([]rune(in.Term))>80||strings.ContainsAny(in.Term,"\r\n") {return fail("unsupported unsafe lexical form")}
 if in.Classification!="public_synthetic" {return fail("private or user-scoped projection cannot leave public runner")}
 if in.DisclosureApprovalRef!="" {return fail("synthetic public harness cannot assert real privileged disclosure approval")}
 hash:=sha256.Sum256([]byte(in.TargetID+"|"+in.PlanRef+"|"+in.FormLanguage+"|"+strings.TrimSpace(in.Term)))
 out.TermDigest=hex.EncodeToString(hash[:])
 out.Status="OFFLINE_PUBLIC_HANDOFF_OK"
 out.Reason="synthetic only; exact private CPE adapter still must execute inside trusted boundary"
 return out,nil
}
