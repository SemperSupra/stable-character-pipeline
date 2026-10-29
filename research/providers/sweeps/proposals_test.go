package sweeps

import "testing"

func TestCPEResearchOnlyCandidate(t *testing.T){
 o:=[]Observation{
  {QueryID:"q1",Term:"Gehbewegung",Language:"de",SourceID:"provider1:item",SourceLineage:"shared-backend",EvidenceRef:"fixture:e1",MappingState:"lexical_gap",MappingRelation:"related"},
  {QueryID:"q2",Term:"Gehbewegung",Language:"de",SourceID:"provider2:item",SourceLineage:"shared-backend",EvidenceRef:"fixture:e2",MappingState:"lexical_gap",MappingRelation:"related"},
  {QueryID:"q3",Term:"Gehbewegung",Language:"de",SourceID:"provider3:item",SourceLineage:"independent",EvidenceRef:"fixture:e3",MappingState:"lexical_gap",MappingRelation:"related"},
  {QueryID:"q4",Term:"walking",Language:"en",SourceID:"provider4:item",SourceLineage:"independent2",EvidenceRef:"fixture:e4",MappingState:"known",MappingRelation:"exact"},
 }
 props,err:=BuildProposals(o,"fixture:CPE-source-snapshot")
 if err!=nil{t.Fatal(err)}
 if len(props)!=1 {t.Fatalf("must not propose known concept: %+v",props)}
 p:=props[0]
 if p.ProposalKind!="lexicalization_candidate"||p.Status!="RESEARCH_ONLY_CANDIDATE"||p.PolicyMutation||p.CanonicalConceptID!=nil||len(p.IndependentSourceLineages)!=2||len(p.SourceEvidenceRefs)!=3 {t.Fatalf("false ontology promotion or ancestry: %+v",p)}
}
func TestCPECases(t *testing.T){
 cases:=[]struct{state,expect string}{
  {"unmapped","unknown_residual_cluster"},
  {"collision","hard_negative_or_collision"},
  {"lexical_gap","lexicalization_candidate"},
  {"source_coverage_gap","coverage_gap"},
 }
 for _,c:=range cases {
  obs:=[]Observation{{QueryID:"q",Term:"walking",Language:"en",SourceID:"p:r",SourceLineage:"ancestry",EvidenceRef:"fixture:1",MappingState:c.state,MappingRelation:"ambiguous"}}
  props,err:=BuildProposals(obs,"fixture:snapshot")
  if err!=nil{t.Fatal(err)}
  if props[0].ProposalKind!=c.expect||props[0].CanonicalConceptID!=nil {t.Fatalf("%s wrong: %+v",c.state,props)}
 }
}
func TestCPERejectMissingSourceOrSnapshot(t *testing.T){
 obs:=[]Observation{{QueryID:"q",Term:"walk",Language:"en",SourceID:"p:r",SourceLineage:"",EvidenceRef:"fixture",MappingState:"unmapped",MappingRelation:"related"}}
 if _,err:=BuildProposals(obs,"snapshot");err==nil{t.Fatal("missing ancestry")}
 obs[0].SourceLineage="family"
 if _,err:=BuildProposals(obs,"");err==nil{t.Fatal("missing source authority")}
 obs[0].MappingState="new_verified_concept"
 if _,err:=BuildProposals(obs,"snapshot");err==nil{t.Fatal("cannot mark accepted knowledge")}
}
