// Offline CLI showing provider operation capabilities and deterministic non-actuating gate decisions.
// No network, user tokens, account linkage, or actual model transfers occur.
package main

import (
  "encoding/json"
  "flag"
  "fmt"
  "os"
  "github.com/SemperSupra/stable-character-pipeline/research/providers/gates"
)
func main() {
 provider:=flag.String("provider","","Optional provider id (empty returns manifest)")
 operation:=flag.String("operation","","One of search/download/upload/storage/online_edit/viewer")
 cred:=flag.Bool("credential-observed",false,"Synthetic credential state ONLY, never read or transmit token")
 scope:=flag.Bool("scope-verified",false,"Synthetic read/write scope assertion")
 entitlement:=flag.Bool("entitlement-verified",false,"Synthetic subscription approval assertion")
 rights:=flag.Bool("rights-verified",false,"Synthetic asset rights assertion")
 approval:=flag.Bool("owner-approved",false,"Synthetic individual action authorization")
 resourceGated:=flag.Bool("resource-gated",false,"Synthetic provider-specific item gate")
 flag.Parse()
 m,err:=gates.Load()
 if err!=nil {fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ")
 if *provider=="" && *operation=="" {if err=enc.Encode(m);err!=nil{os.Exit(1)};return}
 if *provider==""||*operation==""{fmt.Fprintln(os.Stderr,"both -provider and -operation required");os.Exit(2)}
 req:=gates.Request{
   Provider:*provider,Operation:*operation,CredentialPresent:*cred,CredentialScopeAllowed:*scope,
   EntitlementVerified:*entitlement,RightsVerified:*rights,OwnerApproved:*approval,ResourceGated:*resourceGated,
 }
 if err=enc.Encode(gates.Evaluate(m,req));err!=nil{os.Exit(1)}
}
