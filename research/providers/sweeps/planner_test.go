package sweeps

import ("strings";"testing")

func fixture() (Intent,[]Target,Budget){
 return Intent{ID:"original-public-two-person-walk",RequiredAssetKind:"motion",Mode:"frontier_discovery",Classification:"public_synthetic",DefinitionRef:"fixture:walking-v1",Forms:[]Form{
  {Language:"en",Term:"walking cycle",Relation:"exact",EvidenceRef:"fixture:en"},
  {Language:"de",Term:"Gehbewegung",Relation:"related",EvidenceRef:"fixture:de"},
  {Language:"th",Term:"เดิน",Relation:"exact",EvidenceRef:"fixture:th"},
  {Language:"en",Term:"catwalk",Relation:"hard_negative",EvidenceRef:"fixture:neg"},
  {Language:"de",Term:"Gehbewegung",Relation:"related",EvidenceRef:"fixture:de-again"},
 }},[]Target{
  {ProviderID:"example-provider",Engine:"provider_api",Origin:"https://example.org",SourceLineage:"fixture:independent-1",SupportedKinds:[]string{"motion"},PolicyRef:"fixture:policy",PolicyVerified:true,ScopeAllowed:true,MetadataAPIVerified:true},
  {ProviderID:"example-searxng",Engine:"searxng_owned",Origin:"http://127.0.0.1:8888",SourceLineage:"fixture:upstream-search-engine",SupportedKinds:[]string{"motion"},PolicyRef:"fixture:local-only",PolicyVerified:true,ScopeAllowed:true,MetadataAPIVerified:true},
 },Budget{TotalQueries:6,MaxPerProvider:3,MaxLanguages:3}
}
func TestPlanMultilingualSynthetic(t *testing.T){
 intent,targets,b:=fixture()
 p,err:=PlanSynthetic(intent,targets,b)
 if err!=nil{t.Fatal(err)}
 if len(p.Queries)!=6||!p.NoNetwork||!p.NoOntologyMutation {t.Fatalf("unsafe plan: %+v",p)}
 languages:=map[string]int{};ids:=map[string]bool{}
 for _,q:=range p.Queries{
  languages[q.Language]++
  if q.Term=="catwalk"||q.Semantics!="RETRIEVAL_ONLY_NOT_CONCEPT_EVIDENCE"{t.Fatalf("negative/semantic contamination: %+v",q)}
  if ids[q.QueryID]{t.Fatal("duplicate query ID")};ids[q.QueryID]=true
 }
 if languages["en"]!=2||languages["de"]!=2||languages["th"]!=2{t.Fatalf("language coverage error: %+v",languages)}
 if len(p.Skipped)==0 {t.Fatal("missing negative and duplicate receipts")}
}
func TestPlanKnownProjection(t *testing.T){
 intent,targets,b:=fixture()
 intent.Mode="known_projection";intent.DefinitionRef="";intent.ConceptRef="fixture:concept";intent.ProjectionRef="fixture:opaque-projection"
 if _,err:=PlanSynthetic(intent,targets,b);err!=nil{t.Fatal(err)}
 intent.ProjectionRef=""
 if _,err:=PlanSynthetic(intent,targets,b);err==nil{t.Fatal("missing CPE projection must fail")}
}
func TestPlanRejectPrivateAndInventedLanguage(t *testing.T) {
 intent,targets,b:=fixture()
 intent.Classification="private_protected"
 if _,err:=PlanSynthetic(intent,targets,b);err==nil{t.Fatal("private CPE disclosure not rejected")}
 intent.Classification="public_synthetic"
 intent.Forms=append(intent.Forms,Form{Language:"zh-hans",Term:"步行",Relation:"no_equivalent",EvidenceRef:"fixture:zh"})
 if _,err:=PlanSynthetic(intent,targets,b);err==nil{t.Fatal("over budget languages must fail")}
}
func TestPolicyFailures(t *testing.T){
 intent,targets,b:=fixture()
 targets[0].PolicyVerified=false
 p,err:=PlanSynthetic(intent,targets,b)
 if err!=nil{t.Fatal(err)}
 if len(p.Queries)!=3||!strings.Contains(strings.Join(p.Skipped,","),"POLICY_OR_API_HOLD"){t.Fatalf("policy bypass: %+v",p)}
}
func TestPlanNoEquivalentNeverTranslated(t *testing.T){
 intent,targets,b:=fixture()
 intent.Forms=[]Form{{Language:"de",Term:"kein Äquivalent",Relation:"no_equivalent",EvidenceRef:"fixture:negative"}}
 if _,err:=PlanSynthetic(intent,targets,b);err==nil{t.Fatal("no equivalent should not silently create translated query")}
}
func TestAncestryCollapse(t *testing.T){
 sources,err:=ValidateNoSharedAncestry([]string{"provider-shared","provider-shared","independent"})
 if err!=nil||len(sources)!=2 {t.Fatalf("bad independent count: %v %v",sources,err)}
 if err:=CanShareObservedLineage("same","same");err==nil{t.Fatal("double counting ancestry")}
}
func TestOnlySourceNeutralScopes(t *testing.T){
 for _,s:=range []string{"download","publish","delete","training"}{
  if err:=SafeScope(s);err==nil{t.Fatalf("scope %s should not be permitted",s)}
 }
 if err:=SafeScope("search_only");err!=nil{t.Fatal(err)}
}

func TestCapabilityMismatchStopsUnrelatedSearch(t *testing.T){
 intent,targets,b:=fixture()
 targets[0].SupportedKinds=[]string{"environment","model"}
 plan,err:=PlanSynthetic(intent,targets,b)
 if err!=nil{t.Fatal(err)}
 if len(plan.Queries)!=3||!strings.Contains(strings.Join(plan.Skipped,","),"CAPABILITY_MISMATCH"){t.Fatalf("search fanout into unrelated model library: %+v",plan)}
 targets[0].SupportedKinds=nil
 plan,err=PlanSynthetic(intent,targets,b)
 if err!=nil||!strings.Contains(strings.Join(plan.Skipped,","),"CAPABILITY_UNVERIFIED"){t.Fatalf("unverified capability escaped: %+v %v",plan,err)}
}
