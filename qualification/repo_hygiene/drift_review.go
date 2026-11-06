// Public-only exact GitHub compare evidence, no mutation actions.
// Source evidence differs from branch-name ancestry; disjoint files DO NOT imply merge authority.
package main

import (
 "context"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "net/http"
 "regexp"
 "sort"
 "strings"
 "time"
)

type CompareRef struct {SHA string `json:"sha"`}
type CompareFile struct {Filename string `json:"filename"`}
type CompareResponse struct {
 Status string `json:"status"`
 AheadBy int `json:"ahead_by"`
 BehindBy int `json:"behind_by"`
 TotalCommits int `json:"total_commits"`
 MergeBaseCommit CompareRef `json:"merge_base_commit"`
 Files []CompareFile `json:"files"`
}
type DriftReview struct {
 ChildPR int `json:"child_pr"`
 ParentPR int `json:"parent_pr"`
 RecordedBaseSHA string `json:"recorded_base_sha"`
 ParentCurrentSHA string `json:"parent_current_sha"`
 ChildCurrentSHA string `json:"child_current_sha"`
 ParentNewCommits int `json:"parent_new_commits"`
 ChildNewCommits int `json:"child_new_commits"`
 CurrentDivergenceAhead int `json:"current_divergence_ahead"`
 CurrentDivergenceBehind int `json:"current_divergence_behind"`
 CurrentMergeBase string `json:"current_merge_base"`
 ParentModifiedPaths []string `json:"parent_modified_paths"`
 ChildModifiedPaths []string `json:"child_modified_paths"`
 SharedModifiedPaths []string `json:"shared_modified_paths"`
 Classification string `json:"classification"`
 Action string `json:"action"`
}
type DriftReviewReport struct{
 Schema string `json:"schema"`
 Repo string `json:"repo"`
 AsOf string `json:"as_of"`
 Count int `json:"count"`
 SourceComplete bool `json:"source_complete"`
 Reviews []DriftReview `json:"reviews"`
 Mutations int `json:"mutations"`
 OwnerApproval bool `json:"owner_approval"`
}
type compareFunc func(context.Context,string,string)(CompareResponse,error)
var shaPattern=regexp.MustCompile(`^[a-f0-9]{40}$`)

func makeGithubCompare(token string) compareFunc {
 client:=&http.Client{Timeout:15*time.Second}
 return func(ctx context.Context, base,head string)(CompareResponse,error){
  if token==""||!shaPattern.MatchString(base)||!shaPattern.MatchString(head){
   return CompareResponse{},errors.New("INVALID_TOKEN_OR_SHA")
  }
  addr:="https://api.github.com/repos/"+allowedRepo+"/compare/"+base+"..."+head
  req,err:=http.NewRequestWithContext(ctx,"GET",addr,nil)
  if err!=nil{return CompareResponse{},err}
  req.Header.Set("Authorization","Bearer "+token)
  req.Header.Set("Accept","application/vnd.github+json")
  req.Header.Set("X-GitHub-Api-Version","2022-11-28")
  res,err:=client.Do(req)
  if err!=nil{return CompareResponse{},err}
  defer res.Body.Close()
  if res.StatusCode!=200{
   io.Copy(io.Discard,io.LimitReader(res.Body,2048))
   return CompareResponse{},fmt.Errorf("SOURCE_COMPARE_HTTP_%d",res.StatusCode)
  }
  var data CompareResponse
  if err=json.NewDecoder(io.LimitReader(res.Body,8<<20)).Decode(&data);err!=nil{
   return CompareResponse{},err
  }
  return data,nil
 }
}
func distinctPaths(in []CompareFile)([]string,error){
 if len(in)>=300 {return nil,errors.New("GITHUB_COMPARE_FILE_LIST_LIMIT_REACHED")}
 d:=map[string]bool{}
 for _,f:=range in{
  name:=f.Filename
  if name==""||strings.ContainsRune(name,rune(10))||strings.ContainsRune(name,rune(13)){
   return nil,errors.New("UNTRUSTED_COMPARE_FILE_NAME")
  }
  d[name]=true
 }
 out:=make([]string,0,len(d))
 for name:=range d{out=append(out,name)}
 sort.Strings(out)
 return out,nil
}
func intersectPaths(a,b []string)[]string{
 known:=map[string]bool{};out:=[]string{}
 for _,s:=range a{known[s]=true}
 for _,s:=range b{if known[s]{out=append(out,s)}}
 sort.Strings(out)
 return out
}
func inspectDrifts(ctx context.Context,s Snapshot,ws Workset,compare compareFunc)(DriftReviewReport,error){
 if !s.Complete||!ws.Complete||s.Repo!=allowedRepo||ws.Repo!=allowedRepo||
    len(ws.BaseSHADrifts)>32 {return DriftReviewReport{},errors.New("DRIFT_SOURCE_INCOMPLETE_OR_BUDGET_EXCEEDED")}
 byID:=map[int]Pull{}
 for _,p:=range s.PRs{byID[p.Number]=p}
 report:=DriftReviewReport{Schema:"scp.r009.hygiene_source_divergence_review.v1",
  Repo:s.Repo,AsOf:s.AsOf,SourceComplete:true,Mutations:0,OwnerApproval:false,
  Reviews:[]DriftReview{}}
 for _,d:=range ws.BaseSHADrifts{
  parent,okp:=byID[d.ParentPR];child,okc:=byID[d.ChildPR]
  if !okp||!okc||!shaPattern.MatchString(parent.Head.SHA)||!shaPattern.MatchString(child.Head.SHA)||
     parent.Head.SHA!=d.ObservedParentHeadSHA||child.Base.SHA!=d.ObservedBaseSHA{
   return DriftReviewReport{},fmt.Errorf("STALE_OR_INVALID_DRIFT_HEADS_CHILD_%d",d.ChildPR)
  }
  old:=d.ObservedBaseSHA
  pa,err:=compare(ctx,old,parent.Head.SHA);if err!=nil{return DriftReviewReport{},fmt.Errorf("PARENT_COMPARE_CHILD_%d: %w",d.ChildPR,err)}
  ch,err:=compare(ctx,old,child.Head.SHA);if err!=nil{return DriftReviewReport{},fmt.Errorf("CHILD_COMPARE_CHILD_%d: %w",d.ChildPR,err)}
  dv,err:=compare(ctx,parent.Head.SHA,child.Head.SHA);if err!=nil{return DriftReviewReport{},fmt.Errorf("DIVERGENCE_COMPARE_CHILD_%d: %w",d.ChildPR,err)}
  pr,err:=distinctPaths(pa.Files);if err!=nil{return DriftReviewReport{},fmt.Errorf("PARENT_PATHS_CHILD_%d: %w",d.ChildPR,err)}
  cr,err:=distinctPaths(ch.Files);if err!=nil{return DriftReviewReport{},fmt.Errorf("CHILD_PATHS_CHILD_%d: %w",d.ChildPR,err)}
  overlap:=intersectPaths(pr,cr)
  classification:="HISTORY_UNVERIFIED_HELD"
  if pa.Status=="ahead"&&pa.BehindBy==0&&ch.Status=="ahead"&&ch.BehindBy==0&&
     dv.Status=="diverged"&&dv.MergeBaseCommit.SHA==old&&dv.AheadBy>0&&dv.BehindBy>0{
   if len(overlap)==0{classification="DISJOINT_PATHS_REVIEW_ONLY"}else{classification="SHARED_PATHS_CONFLICT_REVIEW"}
  }
  report.Reviews=append(report.Reviews,DriftReview{
   ChildPR:d.ChildPR,ParentPR:d.ParentPR,RecordedBaseSHA:old,
   ParentCurrentSHA:parent.Head.SHA,ChildCurrentSHA:child.Head.SHA,
   ParentNewCommits:pa.AheadBy,ChildNewCommits:ch.AheadBy,
   CurrentDivergenceAhead:dv.AheadBy,CurrentDivergenceBehind:dv.BehindBy,
   CurrentMergeBase:dv.MergeBaseCommit.SHA,
   ParentModifiedPaths:pr,ChildModifiedPaths:cr,SharedModifiedPaths:overlap,
   Classification:classification,Action:"RETAIN_UNMERGED_OWNER_AND_EXACT_CI_REVIEW_REQUIRED"})
 }
 report.Count=len(report.Reviews)
 return report,nil
}
func (r DriftReviewReport)Markdown()string{
 var b strings.Builder
 fmt.Fprintf(&b, `# SHA drift source compare — public read-only

As of %s UTC, **%d drifted PRs**, mutations **0**. These are exact GitHub compare source paths. Disjoint paths do **not** waive owner, rights, CI, custody or promotion gates.

`,r.AsOf,r.Count)
 b.WriteString(`| Child / parent | Parent new commits | Child new commits | Current ahead / behind | Shared paths | Classification |
|---|---:|---:|---:|---|---|
`)
 for _,d:=range r.Reviews{
  fmt.Fprintf(&b, `| #%d / #%d | %d | %d | %d / %d | %s | %s |
`,d.ChildPR,d.ParentPR,d.ParentNewCommits,d.ChildNewCommits,
    d.CurrentDivergenceAhead,d.CurrentDivergenceBehind,
    strings.Join(d.SharedModifiedPaths,", "),d.Classification)
 }
 return b.String()
}
func (r DriftReviewReport)JSON()[]byte{
 v,_:=json.MarshalIndent(r,"","  ");return append(v,byte(10))
}
