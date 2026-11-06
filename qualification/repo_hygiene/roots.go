// Root-workset planning is GET-only and does not grant merge or close authority.
package main

import (
 "encoding/json"
 "errors"
 "fmt"
 "sort"
 "strings"
)

type BaseSHADrift struct {
 ChildPR int `json:"child_pr"`
 ParentPR int `json:"parent_pr"`
 ObservedBaseSHA string `json:"observed_base_sha"`
 ObservedParentHeadSHA string `json:"observed_parent_head_sha"`
 Disposition string `json:"disposition"`
}
type RootGroup struct {
 RootPR int `json:"root_pr"`
 RootTitle string `json:"root_title"`
 RootBranch string `json:"root_branch"`
 DirectChildren int `json:"direct_children"`
 TotalDescendants int `json:"total_descendants"`
 MaxDepth int `json:"max_depth"`
 DriftedChildren []int `json:"base_sha_drifted_children"`
 Members []int `json:"members"`
 Disposition string `json:"disposition"`
}
type Workset struct {
 Schema string `json:"schema"`
 Repo string `json:"repo"`
 AsOf string `json:"as_of"`
 Complete bool `json:"complete"`
 TotalOpen int `json:"total_open"`
 RootCount int `json:"root_count"`
 StackedCount int `json:"stacked_count"`
 BaseSHADriftCount int `json:"base_sha_drift_count"`
 BaseSHADrifts []BaseSHADrift `json:"base_sha_drifts"`
 Groups []RootGroup `json:"groups"`
 Mutations int `json:"mutations"`
 Interpretation string `json:"interpretation"`
}
func buildWorkset(snapshot Snapshot) (Workset,error){
 if snapshot.Schema!=schema || snapshot.Repo!=allowedRepo || !snapshot.Complete {
  return Workset{},errors.New("INCOMPLETE_OR_UNTRUSTED_SNAPSHOT")
 }
 if _,err:=audit(snapshot,14);err!=nil{return Workset{},fmt.Errorf("SNAPSHOT_INVALID: %w",err)}
 byRef:=map[string]*Pull{};parents:=map[int]int{}
 driftByChild:=map[int]BaseSHADrift{}
 for i:=range snapshot.PRs{
  p:=&snapshot.PRs[i]
  if byRef[p.Head.Ref]!=nil{return Workset{},fmt.Errorf("DUPLICATE_HEAD_REF:%d",p.Number)}
  byRef[p.Head.Ref]=p
 }
 rootByPR:=map[int]*RootGroup{}
 roots:=map[int]int{}
 depth:=map[int]int{}
 visiting:=map[int]bool{}
 var visit func(*Pull)(int,int,error)
 visit=func(p *Pull)(int,int,error){
  if visiting[p.Number]{return 0,0,fmt.Errorf("CYCLE_AT_PR:%d",p.Number)}
  if root,exists:=roots[p.Number];exists{return root,depth[p.Number],nil}
  visiting[p.Number]=true
  var root,d int
  if p.Base.Ref=="main" || p.Base.Ref=="master" {
   root=p.Number;d=0
  }else{
   parent,found:=byRef[p.Base.Ref]
   if !found{return 0,0,fmt.Errorf("MISSING_OPEN_PARENT:%d:%s",p.Number,p.Base.Ref)}
   if p.Base.SHA!=parent.Head.SHA{
    driftByChild[p.Number]=BaseSHADrift{ChildPR:p.Number,ParentPR:parent.Number,
      ObservedBaseSHA:p.Base.SHA,ObservedParentHeadSHA:parent.Head.SHA,
      Disposition:"BASE_SHA_DRIFT_HELD_NO_MERGE_CLOSE_DELETE"}
   }
   parents[p.Number]=parent.Number
   r,dep,err:=visit(parent);if err!=nil{return 0,0,err}
   root=r;d=dep+1
  }
  visiting[p.Number]=false
  roots[p.Number]=root;depth[p.Number]=d
  return root,d,nil
 }
 for i:=range snapshot.PRs {
  p:=&snapshot.PRs[i]
  if _,_,err:=visit(p);err!=nil{return Workset{},err}
 }
 for _,p:=range snapshot.PRs{
  if p.Number==roots[p.Number]{
   rootByPR[p.Number]=&RootGroup{RootPR:p.Number,RootTitle:p.Title,RootBranch:p.Head.Ref,Disposition:"RETAIN_AND_REVIEW_WITH_OWNER_GATES"}
  }
 }
 for _,p:=range snapshot.PRs{
  root:=rootByPR[roots[p.Number]]
  if root==nil{return Workset{},fmt.Errorf("ROOT_NOT_FOUND_FOR:%d",p.Number)}
  root.Members=append(root.Members,p.Number)
  if depth[p.Number]>root.MaxDepth{root.MaxDepth=depth[p.Number]}
  if p.Number!=root.RootPR{root.TotalDescendants++}
  if parents[p.Number]==root.RootPR{root.DirectChildren++}
  if _,isDrift:=driftByChild[p.Number];isDrift{root.DriftedChildren=append(root.DriftedChildren,p.Number)}
 }
 ws:=Workset{Schema:"scp.r009.hygiene_root_workset.v1",Repo:snapshot.Repo,
  AsOf:snapshot.AsOf,Complete:true,TotalOpen:len(snapshot.PRs),
  RootCount:len(rootByPR),Mutations:0,
  Interpretation:"Graph uses observed open-PR base BRANCH names. Any mismatch between recorded base SHA and current parent HEAD is explicitly BASE_SHA_DRIFT_HELD. The graph is NOT proof of source equivalence, tested CI, permission to merge, close, delete, release or deploy."}
 for _,grp:=range rootByPR{
  sort.Ints(grp.Members)
  sort.Ints(grp.DriftedChildren)
  ws.StackedCount+=grp.TotalDescendants
  ws.Groups=append(ws.Groups,*grp)
 }
 sort.Slice(ws.Groups,func(i,j int)bool{
  if ws.Groups[i].TotalDescendants==ws.Groups[j].TotalDescendants{return ws.Groups[i].RootPR<ws.Groups[j].RootPR}
  return ws.Groups[i].TotalDescendants>ws.Groups[j].TotalDescendants
 })
 for _,d:=range driftByChild{ws.BaseSHADrifts=append(ws.BaseSHADrifts,d)}
 sort.Slice(ws.BaseSHADrifts,func(i,j int)bool{return ws.BaseSHADrifts[i].ChildPR<ws.BaseSHADrifts[j].ChildPR})
 ws.BaseSHADriftCount=len(ws.BaseSHADrifts)
  if ws.RootCount+ws.StackedCount!=ws.TotalOpen{return Workset{},errors.New("GRAPH_INCONSISTENT")}
 return ws,nil
}
func (ws Workset) Markdown()string{
 var b strings.Builder
 fmt.Fprintf(&b, `# Public PR dependency roots — review-only

As of %s UTC: **%d open PRs**, **%d default-branch roots**, **%d descendants**, **%d base-SHA drift holds**, **%d mutations**.

`, ws.AsOf,ws.TotalOpen,ws.RootCount,ws.StackedCount,ws.BaseSHADriftCount,ws.Mutations)
 b.WriteString(`These are **branch-name dependencies** with exact SHA-drift holds, not proof of redundant code or permission to merge/close/delete. Every disposition remains held pending exact-source, CI, rights, custody and owner authorization.

`)
 b.WriteString(`| Root PR | Descendants | Immediate children | SHA drift holds | Max depth | Required review |
|---|---:|---:|---:|---:|---|
`)
 for _,g:=range ws.Groups{
  fmt.Fprintf(&b, `| #%d | %d | %d | %d | %d | %s |
`,g.RootPR,g.TotalDescendants,g.DirectChildren,len(g.DriftedChildren),g.MaxDepth,g.Disposition)
 }
 if len(ws.BaseSHADrifts)>0{
  b.WriteString("### Held SHA-drifted child PRs (observed source snapshot)\n\n")
  for _,drift:=range ws.BaseSHADrifts{
   fmt.Fprintf(&b,"- child #%d → parent #%d: BASE_SHA_DRIFT_HELD. Verify exact commits and first failures before any change.\n",drift.ChildPR,drift.ParentPR)
  }
 }
  return b.String()
}
func (ws Workset) JSON()[]byte{
 out,_:=json.MarshalIndent(ws,"","  ")
 return append(out,byte(10))
}
