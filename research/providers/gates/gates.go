// Package gates evaluates documented provider operation support without handling real credentials.
// All positive decisions are readiness candidates, never actual authorization to access a provider.
package gates

import (
  _ "embed"
  "encoding/json"
  "errors"
  "fmt"
  "strings"
)

//go:embed providers.v1.json
var manifestBytes []byte

type Operation struct {
  API string `json:"api"`
  Web string `json:"web"`
  Auth string `json:"auth"`
  Notes string `json:"notes,omitempty"`
}
type Provider struct {
  ID string `json:"provider_id"`
  Name string `json:"name"`
  AuthModes []string `json:"auth_modes"`
  EvidenceURL string `json:"evidence_url"`
  Operations map[string]Operation `json:"operations"`
}
type Manifest struct {
  Schema string `json:"schema"`
  Status string `json:"status"`
  Providers []Provider `json:"providers"`
}
type Request struct {
  Provider string `json:"provider"`
  Operation string `json:"operation"`
  ResourceGated bool `json:"resource_gated"`
  CredentialPresent bool `json:"credential_present"`
  CredentialScopeAllowed bool `json:"credential_scope_allowed"`
  EntitlementVerified bool `json:"entitlement_verified"`
  RightsVerified bool `json:"rights_verified"`
  OwnerApproved bool `json:"owner_approved"`
}
type Decision struct {
  Schema string `json:"schema"`
  Provider string `json:"provider"`
  Operation string `json:"operation"`
  APIStatus string `json:"api_status"`
  WebsiteStatus string `json:"website_status"`
  Status string `json:"status"`
  Actuated bool `json:"actuated"`
  CredentialExchanged bool `json:"credential_exchanged"`
  Reason string `json:"reason"`
}
func Load() (Manifest,error) {
  var m Manifest
  if err:=json.Unmarshal(manifestBytes,&m); err!=nil{return m,err}
  if m.Schema!="scp.provider_operations.v1"||len(m.Providers)==0 {return m,errors.New("unsupported manifest")}
  allowedAPI:=map[string]bool{"public":true,"gated":true,"conditional":true,"enterprise":true,"not_documented":true,"not_offered":true}
  allowedWeb:=map[string]bool{"yes":true,"limited":true,"source-link":true,"unknown":true,"no":true}
  seen:=map[string]bool{}
  required:=[]string{"search","download","upload","storage","online_edit","viewer"}
  for _,p:=range m.Providers {
    if p.ID==""||p.Name==""||seen[p.ID]||!strings.HasPrefix(p.EvidenceURL,"https://"){return m,fmt.Errorf("invalid provider declaration %q",p.ID)}
    seen[p.ID]=true
    for _,k:=range required {
      o,ok:=p.Operations[k]
      if !ok||!allowedAPI[o.API]||!allowedWeb[o.Web] {return m,fmt.Errorf("invalid %s.%s",p.ID,k)}
      if (o.API=="gated"||o.API=="enterprise")&&o.Auth=="none" {return m,fmt.Errorf("missing auth claim %s.%s",p.ID,k)}
    }
  }
  return m,nil
}
func Evaluate(m Manifest, req Request) Decision {
  out:=Decision{Schema:"scp.provider_operation_decision.v1",Provider:req.Provider,Operation:req.Operation,Status:"NO_PROVIDER",Actuated:false,CredentialExchanged:false,Reason:"Provider not found in documentation snapshot"}
  var p *Provider
  for i:=range m.Providers {if m.Providers[i].ID==req.Provider {p=&m.Providers[i];break}}
  if p==nil{return out}
  o,ok:=p.Operations[req.Operation]
  if !ok {out.Status="UNKNOWN_OPERATION";out.Reason="Operation not declared";return out}
  out.APIStatus=o.API;out.WebsiteStatus=o.Web
  switch o.API {
  case "not_documented":
    out.Status="UNDOCUMENTED_API";out.Reason="Website feature is not a verified API contract";return out
  case "not_offered":
    out.Status="UNAVAILABLE";out.Reason="Operation is not offered through provider API";return out
  case "enterprise":
    if !req.EntitlementVerified {out.Status="ENTITLEMENT_REQUIRED";out.Reason="Independent plan/enterprise entitlement proof required";return out}
  }
  gated:=o.API=="gated"||o.API=="enterprise"||(o.API=="conditional"&&req.ResourceGated)
  if gated&&!req.CredentialPresent {out.Status="AUTH_REQUIRED";out.Reason="Real provider auth must be separately connected outside public source runner";return out}
  if gated&&!req.CredentialScopeAllowed {out.Status="SCOPE_REQUIRED";out.Reason="Provider operation scope not verified";return out}
  if req.Operation=="download"||req.Operation=="upload"||req.Operation=="online_edit"||req.Operation=="storage" {
    if !req.RightsVerified {out.Status="RIGHTS_UNKNOWN";out.Reason="Object-specific usage and transfer rights are not verified";return out}
    if !req.OwnerApproved {out.Status="OWNER_APPROVAL_REQUIRED";out.Reason="No explicit scoped operation admission";return out}
  }
  out.Status="READY_CANDIDATE"
  out.Reason="Only static gate predicates satisfied; real session, account, rights, transport, and object require independent runtime validation"
  return out
}
