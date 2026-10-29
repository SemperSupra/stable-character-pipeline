package gates

import "testing"

func TestManifestComplete(t *testing.T) {
 m,err:=Load()
 if err!=nil {t.Fatal(err)}
 if len(m.Providers)!=22 {t.Fatalf("expected 22 providers, got %d",len(m.Providers))}
 for _,p:=range m.Providers {
   if len(p.Operations)!=6 {t.Fatalf("%s missing operations",p.ID)}
 }
}
func TestNoSecretStorage(t *testing.T) {
 m,err:=Load()
 if err!=nil{t.Fatal(err)}
 for _,p:=range m.Providers{
   if p.ID=="sketchfab" && p.Operations["download"].API!="gated" {t.Fatal("Sketchfab auth lost")}
   if p.ID=="polycam" && p.Operations["download"].API!="enterprise" {t.Fatal("Polycam enterprise gate lost")}
 }
}
func TestGates(t *testing.T) {
 m,err:=Load()
 if err!=nil{t.Fatal(err)}
 cases:=[]struct{name string; request Request; want string}{
  {"public search",Request{Provider:"polyhaven",Operation:"search"},"READY_CANDIDATE"},
  {"public download missing rights",Request{Provider:"polyhaven",Operation:"download"},"RIGHTS_UNKNOWN"},
  {"public download missing owner",Request{Provider:"polyhaven",Operation:"download",RightsVerified:true},"OWNER_APPROVAL_REQUIRED"},
  {"public download admitted predicate",Request{Provider:"polyhaven",Operation:"download",RightsVerified:true,OwnerApproved:true},"READY_CANDIDATE"},
  {"Sketchfab no login",Request{Provider:"sketchfab",Operation:"download"},"AUTH_REQUIRED"},
  {"Sketchfab no scope",Request{Provider:"sketchfab",Operation:"download",CredentialPresent:true},"SCOPE_REQUIRED"},
  {"Sketchfab no rights",Request{Provider:"sketchfab",Operation:"download",CredentialPresent:true,CredentialScopeAllowed:true},"RIGHTS_UNKNOWN"},
  {"Sketchfab no owner",Request{Provider:"sketchfab",Operation:"download",CredentialPresent:true,CredentialScopeAllowed:true,RightsVerified:true},"OWNER_APPROVAL_REQUIRED"},
  {"Sketchfab admitted predicate",Request{Provider:"sketchfab",Operation:"download",CredentialPresent:true,CredentialScopeAllowed:true,RightsVerified:true,OwnerApproved:true},"READY_CANDIDATE"},
  {"Polycam requires plan first",Request{Provider:"polycam",Operation:"download",CredentialPresent:true},"ENTITLEMENT_REQUIRED"},
  {"Polycam scope required",Request{Provider:"polycam",Operation:"download",EntitlementVerified:true,CredentialPresent:true},"SCOPE_REQUIRED"},
  {"Fab public API unverified",Request{Provider:"fab",Operation:"download",CredentialPresent:true,RightsVerified:true,OwnerApproved:true},"UNDOCUMENTED_API"},
  {"Open3DLab challenge still unverified",Request{Provider:"open3dlab",Operation:"download",CredentialPresent:true,RightsVerified:true,OwnerApproved:true},"UNDOCUMENTED_API"},
  {"Upload without OAuth",Request{Provider:"sketchfab",Operation:"upload",RightsVerified:true,OwnerApproved:true},"AUTH_REQUIRED"},
  {"OAuth does not authorize uploads",Request{Provider:"sketchfab",Operation:"upload",CredentialPresent:true,CredentialScopeAllowed:true,OwnerApproved:true},"RIGHTS_UNKNOWN"},
  {"Unknown provider",Request{Provider:"fake",Operation:"search"},"NO_PROVIDER"},
  {"Unknown op",Request{Provider:"sketchfab",Operation:"delete"},"UNKNOWN_OPERATION"},
  {"Online edit not API",Request{Provider:"sketchfab",Operation:"online_edit",CredentialPresent:true,RightsVerified:true,OwnerApproved:true},"UNDOCUMENTED_API"},
  {"Hugging Face gated file",Request{Provider:"huggingface",Operation:"download",ResourceGated:true},"AUTH_REQUIRED"},
  {"Hugging Face nongated file still requires rights",Request{Provider:"huggingface",Operation:"download",ResourceGated:false},"RIGHTS_UNKNOWN"},
  {"Wikimedia upload no auth",Request{Provider:"wikimedia",Operation:"upload",RightsVerified:true,OwnerApproved:true},"AUTH_REQUIRED"},
  {"No unsupported provider uploading",Request{Provider:"kenney",Operation:"upload",CredentialPresent:true,RightsVerified:true,OwnerApproved:true},"UNAVAILABLE"},
 }
 for _,c:=range cases {
   t.Run(c.name,func(t *testing.T){
     got:=Evaluate(m,c.request)
     if got.Status!=c.want {t.Fatalf("got %s, want %s",got.Status,c.want)}
     if got.Actuated||got.CredentialExchanged {t.Fatal("offline oracle must never call provider")}
   })
 }
}
