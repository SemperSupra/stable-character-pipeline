// Synthetic fixture runner for source-neutral, bounded multilingual qualification.
// No provider network, CPE private data, actual account credentials or ontology writes.
package main

import (
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "github.com/SemperSupra/stable-character-pipeline/research/providers/sweeps"
)
func main(){
 lane:=flag.String("lane","","plan|citizen|cpe")
 flag.Parse()
 enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ")
 var output any
 switch *lane{
 case "plan":
  intent:=sweeps.Intent{ID:"synthetic-walking-motion",RequiredAssetKind:"motion",Mode:"frontier_discovery",Classification:"public_synthetic",DefinitionRef:"fixture:2actor-walk-v1",
   Forms:[]sweeps.Form{
    {Language:"en",Term:"walking motion",EvidenceRef:"fixture:en",Relation:"exact"},
    {Language:"de",Term:"Gehbewegung",EvidenceRef:"fixture:de",Relation:"related"},
    {Language:"th",Term:"การเดิน",EvidenceRef:"fixture:th",Relation:"exact"},
    {Language:"en",Term:"catwalk",EvidenceRef:"fixture:hardnegative",Relation:"hard_negative"},
   }}
  targets:=[]sweeps.Target{{ProviderID:"synthetic-provider",Engine:"provider_api",Origin:"https://example.org",SourceLineage:"fixture:provider-1",SupportedKinds:[]string{"motion"},
   PolicyRef:"fixture:only",PolicyVerified:true,ScopeAllowed:true,MetadataAPIVerified:true}}
  p,err:=sweeps.PlanSynthetic(intent,targets,sweeps.Budget{TotalQueries:3,MaxPerProvider:3,MaxLanguages:3})
  if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
  output=p
 case "citizen":
  p:=sweeps.AccessPolicy{ProviderID:"synthetic-provider",PolicyRef:"fixture:preapproved-simulation",Verified:true,TermsPermit:true,
   Operation:"search_only",Method:"documented_api",UserAgent:"StableCharacterPipeline/Research (+https://github.com/SemperSupra/stable-character-pipeline/issues/19)",
   MaxPerMinute:2,MaxPerDay:5,MaxConcurrency:1,MinGapMS:5000,MaxPages:2,MaxResponseBytes:32768,CacheTTLSeconds:3600}
  states:=[]any{sweeps.CheckPermit(p,sweeps.RequestState{},1000)}
  s,err:=sweeps.AfterResponse(sweeps.RequestState{},429,60,1000)
  if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
  states=append(states,sweeps.CheckPermit(p,s,10000),sweeps.CheckPermit(p,s,61000))
  output=map[string]any{"schema":"scp.citizen_research_receipt.v1","synthetic":true,"decisions":states,"request_count":0,"network_used":false}
 case "cpe":
  observations:=[]sweeps.Observation{
   {QueryID:"fixture:q1",Term:"Gehbewegung",Language:"de",SourceID:"p1:r1",SourceLineage:"shared-upstream",EvidenceRef:"fixture:de1",MappingState:"lexical_gap",MappingRelation:"related"},
   {QueryID:"fixture:q2",Term:"Gehbewegung",Language:"de",SourceID:"p2:r1",SourceLineage:"shared-upstream",EvidenceRef:"fixture:de2",MappingState:"lexical_gap",MappingRelation:"related"},
   {QueryID:"fixture:q3",Term:"Gehbewegung",Language:"de",SourceID:"p3:r2",SourceLineage:"distinct-upstream",EvidenceRef:"fixture:de3",MappingState:"lexical_gap",MappingRelation:"related"},
  }
  p,err:=sweeps.BuildProposals(observations,"fixture:research-only-snapshot")
  if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
  output=map[string]any{"schema":"scp.cpe_feedback_research.v1","accepted_concept_mutations":0,"source_not_authority":true,"proposals":p}
 default:
  fmt.Fprintln(os.Stderr,"-lane must be plan, citizen, or cpe");os.Exit(2)
 }
 if err:=enc.Encode(output);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
}
