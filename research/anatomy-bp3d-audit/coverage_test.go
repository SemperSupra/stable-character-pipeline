package main

import "testing"
func TestCoverageNeverPromotesMeshByName(t *testing.T){
 isa:=map[string]Item{"FMA7310":{"FMA7310","BP1","left lung"}}
 part:=map[string]Item{"FMA7310":{"FMA7310","BP2","left lung"}}
 rep:=computeCoverage(isa,part,[]Target{{"respiratory","left lung",nil},{"sensory","eye",[]string{"eyeball"}}})
 if rep.Targets!=2||rep.ExactReferenceNames!=1||rep.NoNameHit!=1{t.Fatalf("%+v",rep)}
 x:=rep.Rows[0]
 if x.GeometryStatus!="UNKNOWN_NOT_IMPORTED"||x.Status!="EXACT_SOURCE_LABEL_UNREVIEWED"||len(x.Candidates)!=2{
  t.Fatalf("unsafe name->mesh promotion %+v",x)
 }
 if x.Candidates[0].RepresentationID==x.Candidates[1].RepresentationID{t.Fatal("source view geometry identity collapsed")}
}
func TestLexicalAliasCandidatesRemainUnreviewed(t *testing.T){
 m:=map[string]Item{
  "FMA1":{"FMA1","BP1","globe of left eye"},
  "FMA2":{"FMA2","BP2","eye socket"},
  "FMA3":{"FMA3","BP3","eyelid"},
 }
 out:=computeCoverage(m,map[string]Item{},[]Target{{"sensory","eye",[]string{"globe of eye"}}})
 if out.Rows[0].Status!="LEXICAL_CANDIDATES_UNREVIEWED"||out.Rows[0].CandidateCount!=2{
  t.Fatalf("eye within eyelid or globe name falsely matched: %+v",out.Rows[0])
 }
}
func TestAllSystemsPresentAsQueriesButNotAsClaimedModels(t *testing.T){
 seen:=map[string]bool{}
 for _,v:=range standardTargets{seen[v.System]=true}
 for _,name:=range []string{"integumentary","skeletal","muscular","respiratory","circulatory","nervous","sensory","digestive","urinary","reproductive","endocrine","lymphatic"}{
  if !seen[name]{t.Fatalf("missing anatomy coverage target group: %s",name)}
 }
 r:=computeCoverage(map[string]Item{},map[string]Item{},standardTargets)
 if r.NoNameHit!=len(standardTargets)||r.ExactReferenceNames!=0{t.Fatal("invented available anatomy")}
}
