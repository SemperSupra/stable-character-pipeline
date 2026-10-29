package sweeps

import (
 "crypto/sha256"
 "encoding/hex"
 "errors"
 "sort"
 "strings"
)
type Observation struct {
 QueryID string `json:"query_id"`
 Term string `json:"term"`
 Language string `json:"language"`
 SourceID string `json:"source_id"`
 SourceLineage string `json:"source_lineage"`
 EvidenceRef string `json:"evidence_ref"`
 MappingState string `json:"mapping_state"`
 MappingRelation string `json:"mapping_relation"`
}
type Proposal struct {
 Schema string `json:"schema"`
 ProposalID string `json:"proposal_id"`
 Producer string `json:"producer"`
 SourceConceptSnapshotRef string `json:"source_concept_snapshot_ref"`
 ProposalKind string `json:"proposal_kind"`
 CandidateTerm string `json:"candidate_term"`
 Language string `json:"language"`
 MappingRelation string `json:"mapping_relation"`
 CanonicalConceptID *string `json:"canonical_concept_id"`
 IndependentSourceLineages []string `json:"independent_source_lineages"`
 SourceEvidenceRefs []string `json:"source_evidence_refs"`
 Uncertainty string `json:"uncertainty"`
 Status string `json:"status"`
 PolicyMutation bool `json:"policy_mutation"`
 ProvenanceNote string `json:"provenance_note"`
}
func BuildProposals(observations []Observation, snapshotRef string) ([]Proposal,error){
 if snapshotRef==""||len(observations)==0||len(observations)>40{return nil,errors.New("missing snapshot or unbounded observations")}
 grouped:=map[string][]Observation{}
 for _,o:=range observations{
  if o.QueryID==""||o.SourceID==""||o.SourceLineage==""||o.EvidenceRef==""||o.Term==""||!ValidLanguage(o.Language) {return nil,errors.New("incomplete evidence/ancestry")}
  switch o.MappingState {case "unmapped","collision","lexical_gap","known": default:return nil,errors.New("invalid mapping-state observation")}
  if o.MappingRelation!="exact"&&o.MappingRelation!="related"&&o.MappingRelation!="ambiguous"&&o.MappingRelation!="no_equivalent" {return nil,errors.New("unsupported mapping relation")}
  key:=o.Language+"|"+strings.ToLower(strings.TrimSpace(o.Term))+"|"+o.MappingState
  grouped[key]=append(grouped[key],o)
 }
 keys:=make([]string,0,len(grouped))
 for key:=range grouped{keys=append(keys,key)}
 sort.Strings(keys)
 out:=[]Proposal{}
 for _,key:=range keys {
  observations:=grouped[key]
  first:=observations[0]
  if first.MappingState=="known"{continue}
  kind:="source_mapping_candidate"
  if first.MappingState=="lexical_gap"{kind="lexicalization_candidate"}
  if first.MappingState=="collision"{kind="hard_negative_or_collision"}
  if first.MappingState=="unmapped"{kind="unknown_residual_cluster"}
  lineages:=map[string]bool{};refs:=map[string]bool{}
  for _,o:=range observations {lineages[o.SourceLineage]=true;refs[o.EvidenceRef]=true}
  ancestry:=make([]string,0,len(lineages));evidence:=make([]string,0,len(refs))
  for key:=range lineages {ancestry=append(ancestry,key)}
  for key:=range refs {evidence=append(evidence,key)}
  sort.Strings(ancestry);sort.Strings(evidence)
  h:=sha256.Sum256([]byte(snapshotRef+"|"+key))
  out=append(out,Proposal{
   Schema:"scp.concept_discovery_proposal_candidate.v1",ProposalID:hex.EncodeToString(h[:8]),
   Producer:"stable-character-provider-sweep",SourceConceptSnapshotRef:snapshotRef,
   ProposalKind:kind,CandidateTerm:first.Term,Language:first.Language,
   MappingRelation:first.MappingRelation,CanonicalConceptID:nil,
   IndependentSourceLineages:ancestry,SourceEvidenceRefs:evidence,
   Uncertainty:"UNADJUDICATED",Status:"RESEARCH_ONLY_CANDIDATE",
   PolicyMutation:false,
   ProvenanceNote:"Retrieval observations only; shared ancestry deduped; CPE #202 adjudicates independently. Counts do not establish semantics.",
  })
 }
 return out,nil
}
