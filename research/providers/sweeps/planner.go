// Package sweeps provides offline, source-neutral planning, not a second CPE query compiler.
// Inputs are already sanctioned search forms from the private CPE projection or PUBLIC SYNTHETIC frontier seeds.
// It never translates terms, accesses networks, or mutates accepted Concept Authority.
package sweeps

import (
 "crypto/sha256"
 "encoding/hex"
 "errors"
 "fmt"
 "sort"
 "strings"
)
type Form struct {
 Language string `json:"language"`
 Term string `json:"term"`
 EvidenceRef string `json:"evidence_ref"`
 Relation string `json:"relation"`
}
type Intent struct {
 ID string `json:"id"`
 Mode string `json:"mode"`
 Classification string `json:"classification"`
 ConceptRef string `json:"concept_ref,omitempty"`
 ProjectionRef string `json:"projection_ref,omitempty"`
 DefinitionRef string `json:"definition_ref,omitempty"`
 Forms []Form `json:"forms"`
}
type Target struct {
 ProviderID string `json:"provider_id"`
 Engine string `json:"engine"`
 Origin string `json:"origin"`
 SourceLineage string `json:"source_lineage"`
 PolicyRef string `json:"policy_ref"`
 PolicyVerified bool `json:"policy_verified"`
 ScopeAllowed bool `json:"scope_allowed"`
 MetadataAPIVerified bool `json:"metadata_api_verified"`
}
type Budget struct {
 TotalQueries int `json:"total_queries"`
 MaxPerProvider int `json:"max_per_provider"`
 MaxLanguages int `json:"max_languages"`
}
type Query struct {
 QueryID string `json:"query_id"`
 Provider string `json:"provider"`
 Engine string `json:"engine"`
 Origin string `json:"origin"`
 Language string `json:"language"`
 Term string `json:"term"`
 EvidenceRef string `json:"evidence_ref"`
 Semantics string `json:"semantics"`
}
type Plan struct {
 Schema string `json:"schema"`
 IntentID string `json:"intent_id"`
 IntentMode string `json:"intent_mode"`
 SourceClassification string `json:"source_classification"`
 ProjectionRef string `json:"projection_ref,omitempty"`
 Queries []Query `json:"queries"`
 Skipped []string `json:"skipped"`
 NoNetwork bool `json:"no_network"`
 NoOntologyMutation bool `json:"no_ontology_mutation"`
}
func ValidLanguage(s string) bool {
 if len(s)<2||len(s)>12{return false}
 for _,c:=range s {if (c<'a'||c>'z')&&c!='-'{return false}}
 return true
}
func PlanSynthetic(intent Intent, targets []Target, b Budget) (Plan,error) {
 out:=Plan{Schema:"scp.multilingual_search_plan.v1",IntentID:intent.ID,IntentMode:intent.Mode,SourceClassification:intent.Classification,ProjectionRef:intent.ProjectionRef,NoNetwork:true,NoOntologyMutation:true}
 if intent.Classification!="public_synthetic" {return out,errors.New("public runner requires only original synthetic query material")}
 if intent.ID==""||len(intent.Forms)==0 {return out,errors.New("missing bounded intent")}
 switch intent.Mode{
 case "known_projection":
  if intent.ConceptRef==""||intent.ProjectionRef==""||intent.DefinitionRef!="" {return out,errors.New("known intent requires pinned approved projection reference")}
 case "frontier_discovery":
  if intent.ConceptRef!=""||intent.ProjectionRef!=""||intent.DefinitionRef=="" {return out,errors.New("frontier discovery cannot invent an accepted concept reference")}
 default: return out,errors.New("unknown CPE mode")
 }
 if b.TotalQueries<1||b.TotalQueries>18||b.MaxPerProvider<1||b.MaxPerProvider>6||b.MaxLanguages<1||b.MaxLanguages>8 {return out,errors.New("budget exceeds hard resource ceiling")}
 if len(targets)>8||len(targets)==0||len(intent.Forms)>24 {return out,errors.New("unbounded provider or form fanout")}
 forms:=append([]Form(nil),intent.Forms...)
 sort.Slice(forms,func(i,j int)bool{if forms[i].Language==forms[j].Language{return forms[i].Term<forms[j].Term};return forms[i].Language<forms[j].Language})
 langs:=map[string]bool{}
 for _,f:=range forms {
  if !ValidLanguage(f.Language)||f.EvidenceRef==""||f.Term==""||len([]rune(f.Term))>80 {return out,errors.New("invalid unsupported or ungrounded lexicalization")}
  if strings.ContainsAny(f.Term,"\r\n") {return out,errors.New("query header/control injection")}
  if f.Relation!="exact"&&f.Relation!="related"&&f.Relation!="hard_negative"&&f.Relation!="no_equivalent" {return out,errors.New("unsupported term relationship")}
  langs[f.Language]=true
 }
 if len(langs)>b.MaxLanguages{return out,errors.New("unapproved language expansion")}
 sortedTargets:=append([]Target(nil),targets...)
 sort.Slice(sortedTargets,func(i,j int)bool{return sortedTargets[i].ProviderID<sortedTargets[j].ProviderID})
 seenProviders:=map[string]bool{}
 seenQueries:=map[string]bool{}
 perProvider:=map[string]int{}
 for _,t:=range sortedTargets {
  if t.ProviderID==""||t.SourceLineage==""||t.PolicyRef==""||t.Origin==""||seenProviders[t.ProviderID] {return out,errors.New("invalid provider/ancestry or duplicate")}
  seenProviders[t.ProviderID]=true
  if t.Engine!="provider_api"&&t.Engine!="searxng_owned" {return out,errors.New("unsupported engine; public SearXNG not admissible")}
  if !t.PolicyVerified||!t.ScopeAllowed||!t.MetadataAPIVerified {out.Skipped=append(out.Skipped,t.ProviderID+":POLICY_OR_API_HOLD");continue}
  for _,f:=range forms{
   if f.Relation=="hard_negative"||f.Relation=="no_equivalent" {out.Skipped=append(out.Skipped,t.ProviderID+":"+f.Language+":NEGATIVE_OR_NO_EQUIVALENT");continue}
   term:=strings.ToLower(strings.TrimSpace(f.Term))
   dedup:=t.ProviderID+"|"+f.Language+"|"+term
   if seenQueries[dedup] {out.Skipped=append(out.Skipped,t.ProviderID+":DUPLICATE");continue}
   seenQueries[dedup]=true
   if len(out.Queries)>=b.TotalQueries||perProvider[t.ProviderID]>=b.MaxPerProvider {out.Skipped=append(out.Skipped,t.ProviderID+":BUDGET_EXHAUSTED");continue}
   h:=sha256.Sum256([]byte(intent.ID+"|"+dedup))
   out.Queries=append(out.Queries,Query{QueryID:hex.EncodeToString(h[:8]),Provider:t.ProviderID,Engine:t.Engine,Origin:t.Origin,Language:f.Language,Term:term,EvidenceRef:f.EvidenceRef,Semantics:"RETRIEVAL_ONLY_NOT_CONCEPT_EVIDENCE"})
   perProvider[t.ProviderID]++
  }
 }
 if len(out.Queries)==0{return out,errors.New("no safely admitted synthetic queries")}
 return out,nil
}
func ValidateNoSharedAncestry(raw []string) ([]string,error) {
 families:=map[string]bool{}
 for _,s:=range raw {if s=="" {return nil,errors.New("missing source ancestry")};families[s]=true}
 keys:=make([]string,0,len(families))
 for s:=range families{keys=append(keys,s)}
 sort.Strings(keys)
 return keys,nil
}
func SafeScope(mode string) error {
 if mode!="read_metadata"&&mode!="search_only" {return fmt.Errorf("scope %q is not supported by research sweeps",mode)}
 return nil
}
