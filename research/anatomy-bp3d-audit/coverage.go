// R036 named anatomy coverage intelligence from verified BodyParts3D metadata.
// A name match is NOT proof of exact medical concept equivalence or 3D geometry.
package main

import (
 "encoding/json"
 "fmt"
 "sort"
 "strings"
 "unicode"
)
const coverageSchema="scp.anatomy.bp3d.lexical_coverage.v1"
type Target struct{
 System string `json:"system"`
 Query string `json:"query"`
 Aliases []string `json:"aliases"`
}
type Candidate struct {
 ConceptID string `json:"concept_id"`
 SourceView string `json:"source_view"`
 RepresentationID string `json:"representation_id"`
 SourceName string `json:"source_name"`
}
type CoverageRow struct {
 System string `json:"system"`
 Query string `json:"query"`
 Status string `json:"status"`
 Candidates []Candidate `json:"candidates"`
 CandidateCount int `json:"candidate_count"`
 Truncated bool `json:"truncated"`
 GeometryStatus string `json:"geometry_status"`
}
type CoverageReceipt struct{
 Schema string `json:"schema"`
 Status string `json:"status"`
 Targets int `json:"targets"`
 ExactReferenceNames int `json:"exact_reference_names"`
 LexicalOnly int `json:"lexical_only"`
 NoNameHit int `json:"no_name_hit"`
 MultipleDistinctConcepts int `json:"multiple_distinct_concepts"`
 Rows []CoverageRow `json:"rows"`
 Warnings []string `json:"warnings"`
}
var standardTargets=[]Target{
 {"integumentary","skin",[]string{"cutis"}},
 {"integumentary","subcutaneous tissue",[]string{"subcutaneous fat","adipose tissue"}},
 {"integumentary","superficial fascia",[]string{}},
 {"skeletal","femur",[]string{"thigh bone"}},
 {"skeletal","tibia",[]string{}},
 {"skeletal","rib",[]string{"costal bone"}},
 {"skeletal","sternum",[]string{"breastbone"}},
 {"skeletal","vertebra",[]string{"vertebral body"}},
 {"skeletal","articular cartilage",[]string{}},
 {"skeletal","ligament",[]string{}},
 {"muscular","quadriceps femoris",[]string{"quadriceps"}},
 {"muscular","biceps brachii",[]string{}},
 {"muscular","diaphragm",[]string{}},
 {"muscular","Achilles tendon",[]string{"calcaneal tendon"}},
 {"muscular","deep fascia",[]string{}},
 {"respiratory","left lung",[]string{}},
 {"respiratory","right lung",[]string{}},
 {"respiratory","trachea",[]string{"windpipe"}},
 {"respiratory","left main bronchus",[]string{"left principal bronchus"}},
 {"respiratory","right main bronchus",[]string{"right principal bronchus"}},
 {"respiratory","pleura",[]string{"pulmonary pleura"}},
 {"circulatory","heart",[]string{}},
 {"circulatory","aorta",[]string{}},
 {"circulatory","vena cava",[]string{"inferior vena cava"}},
 {"circulatory","pulmonary artery",[]string{}},
 {"circulatory","pulmonary vein",[]string{}},
 {"nervous","brain",[]string{"encephalon"}},
 {"nervous","spinal cord",[]string{}},
 {"nervous","sciatic nerve",[]string{}},
 {"nervous","vagus nerve",[]string{}},
 {"sensory","eye",[]string{"eyeball","globe of eye"}},
 {"sensory","inner ear",[]string{"internal ear"}},
 {"sensory","retina",[]string{}},
 {"digestive","esophagus",[]string{"oesophagus"}},
 {"digestive","stomach",[]string{}},
 {"digestive","liver",[]string{}},
 {"digestive","small intestine",[]string{}},
 {"digestive","pancreas",[]string{}},
 {"digestive","tongue",[]string{}},
 {"urinary","kidney",[]string{}},
 {"urinary","urinary bladder",[]string{"bladder"}},
 {"urinary","ureter",[]string{}},
 {"reproductive","uterus",[]string{}},
 {"reproductive","prostate",[]string{}},
 {"reproductive","ovary",[]string{}},
 {"reproductive","testis",[]string{"testicle"}},
 {"endocrine","pituitary gland",[]string{}},
 {"endocrine","thyroid gland",[]string{}},
 {"endocrine","adrenal gland",[]string{}},
 {"lymphatic","spleen",[]string{}},
 {"lymphatic","thymus",[]string{}},
 {"lymphatic","lymph node",[]string{}},
}
func normalizeName(s string)string{
 // Purely lexical matching, not FMA/UBERON semantic equivalence.
 var b strings.Builder
 space:=false
 for _,r:=range strings.ToLower(s){
  if unicode.IsLetter(r)||unicode.IsDigit(r){
   if space&&b.Len()>0{b.WriteByte(' ')}
   b.WriteRune(r);space=false
  }else{space=true}
 }
 return b.String()
}
func lexicalMatches(label,query string)bool{
 // Match word spans, rather than eye appearing inside "eyelid".
 if label==query{return true}
 return strings.Contains(" "+label+" "," "+query+" ")
}
func computeCoverage(isa,part map[string]Item,targets []Target)CoverageReceipt{
 result:=CoverageReceipt{Schema:coverageSchema,Status:"METADATA_LEXICAL_ONLY_NOT_ANATOMICAL_GEOMETRY",
  Rows:[]CoverageRow{},
  Warnings:[]string{
   "English lexical alias is not a reviewed FMA or UBERON equivalence",
   "No named record proves a distinct 3D mesh or gender/phenotype coverage",
   "IS-A representation identifiers differ from PART-OF identifiers for shared FMA concepts",
   "No static reference can establish moving anatomical fit, collisions, physiology, visual fidelity or medical truth",
  }}
 for _,target:=range targets{
  primary:=normalizeName(target.Query)
  terms:=[]string{primary}
  for _,a:=range target.Aliases{
   if v:=normalizeName(a);v!=""{terms=append(terms,v)}
  }
  candidates:=[]Candidate{}
  exact:=[]Candidate{}
  ids:=map[string]bool{}
  add:=func(m map[string]Item,view string){
   for _,p:=range m{
    name:=normalizeName(p.Name)
    isExact:=false
    isPartial:=false
    for _,term:=range terms{
     if name==term{isExact=true;break}
     if lexicalMatches(name,term){isPartial=true}
    }
    if isExact||isPartial{
     c:=Candidate{ConceptID:p.Concept,SourceView:view,RepresentationID:p.Representation,SourceName:p.Name}
     if isExact{exact=append(exact,c)}else{candidates=append(candidates,c)}
     ids[p.Concept]=true
    }
   }
  }
  add(isa,"ISA")
  add(part,"PART_OF")
  sort.Slice(exact,func(i,j int)bool{
   if exact[i].ConceptID==exact[j].ConceptID{return exact[i].SourceView<exact[j].SourceView}
   return exact[i].ConceptID<exact[j].ConceptID
  })
  sort.Slice(candidates,func(i,j int)bool{
   if candidates[i].ConceptID==candidates[j].ConceptID{return candidates[i].SourceView<candidates[j].SourceView}
   return candidates[i].ConceptID<candidates[j].ConceptID
  })
  row:=CoverageRow{System:target.System,Query:target.Query,
   Status:"NO_EXACT_OR_LEXICAL_NAME_FOUND",
   Candidates:[]Candidate{},GeometryStatus:"UNKNOWN_NOT_IMPORTED"}
  if len(exact)>0{
   row.Status="EXACT_SOURCE_LABEL_UNREVIEWED"
   row.Candidates=exact
   result.ExactReferenceNames++
  }else if len(candidates)>0{
   row.Status="LEXICAL_CANDIDATES_UNREVIEWED"
   row.Candidates=candidates
   result.LexicalOnly++
  }else{
   result.NoNameHit++
  }
  row.CandidateCount=len(row.Candidates)
  if len(row.Candidates)>12{row.Candidates=row.Candidates[:12];row.Truncated=true}
  if len(ids)>1{result.MultipleDistinctConcepts++}
  result.Rows=append(result.Rows,row)
 }
 result.Targets=len(result.Rows)
 return result
}
func emitCoverage(isaPath,partPath string)error{
 isa,_,err:=parseItems(isaPath);if err!=nil{return err}
 part,_,err:=parseItems(partPath);if err!=nil{return err}
 report:=computeCoverage(isa,part,standardTargets)
 encoded,err:=json.Marshal(report);if err!=nil{return err}
 fmt.Println("R036_BP3D_COVERAGE_RECEIPT",string(encoded))
 return nil
}
