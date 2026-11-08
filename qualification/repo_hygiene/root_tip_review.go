// Source-exact main reachability census of independent root PR tips.
// All results are read-only review dispositions, never merge/close commands.
package main

import (
 "context"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "net/http"
 "sort"
 "strings"
 "time"
)

type MainBranchResponse struct{
 Commit struct{SHA string `json:"sha"`} `json:"commit"`
}
type RootTip struct{
 PR int `json:"pr"`
 HeadSHA string `json:"head_sha"`
 MainSHA string `json:"main_sha"`
 Ahead int `json:"ahead_of_main"`
 Behind int `json:"behind_main"`
 Divergence string `json:"github_compare_status"`
 Status string `json:"status"`
 Action string `json:"action"`
}
type RootTipReport struct{
 Schema string `json:"schema"`
 Repo string `json:"repo"`
 AsOf string `json:"as_of"`
 MainSHA string `json:"main_sha"`
 SourceComplete bool `json:"source_complete"`
 RootCount int `json:"root_count"`
 RootTipsChecked int `json:"root_tips_checked"`
 IntegratedAncestors int `json:"integrated_ancestors_review_only"`
 UnmergedSourceRoots int `json:"unmerged_source_roots"`
 Diverged int `json:"diverged_roots"`
 OtherHeld int `json:"other_held"`
 Mutations int `json:"mutations"`
 OwnerApproval bool `json:"owner_approval"`
 Tips []RootTip `json:"tips"`
}
func fetchMainSHA(ctx context.Context,token string)(string,error){
 if token==""{return "",errors.New("NO_PUBLIC_GITHUB_READ_TOKEN")}
 req,err:=http.NewRequestWithContext(ctx,"GET","https://api.github.com/repos/"+allowedRepo+"/branches/main",nil)
 if err!=nil{return "",err}
 req.Header.Set("Authorization","Bearer "+token)
 req.Header.Set("Accept","application/vnd.github+json")
 req.Header.Set("X-GitHub-Api-Version","2022-11-28")
 client:=&http.Client{Timeout:15*time.Second}
 resp,err:=client.Do(req);if err!=nil{return "",err}
 defer resp.Body.Close()
 if resp.StatusCode!=200{
  io.Copy(io.Discard,io.LimitReader(resp.Body,2048))
  return "",fmt.Errorf("MAIN_GITHUB_HTTP_%d",resp.StatusCode)
 }
 var root MainBranchResponse
 if err=json.NewDecoder(io.LimitReader(resp.Body,1<<20)).Decode(&root);err!=nil{return "",err}
 if !shaPattern.MatchString(root.Commit.SHA){return "",errors.New("INVALID_MAIN_SHA")}
 return root.Commit.SHA,nil
}
func inspectRootTips(ctx context.Context,s Snapshot,ws Workset,mainSHA string,compare compareFunc)(RootTipReport,error){
 if !s.Complete||!ws.Complete||s.Repo!=allowedRepo||ws.Repo!=allowedRepo||
     !shaPattern.MatchString(mainSHA)||ws.RootCount>100 {
  return RootTipReport{},errors.New("INVALID_ROOT_TIP_WORKSET")
 }
 byNumber:=map[int]Pull{}
 for _,p:=range s.PRs{byNumber[p.Number]=p}
 out:=RootTipReport{Schema:"scp.r009.public_root_tip_reachability.v1",
  Repo:s.Repo,AsOf:s.AsOf,MainSHA:mainSHA,SourceComplete:true,
  RootCount:ws.RootCount,Mutations:0,OwnerApproval:false,Tips:[]RootTip{}}
 for _,g:=range ws.Groups{
  if g.TotalDescendants!=0{continue}
  p,exists:=byNumber[g.RootPR]
  if !exists||!shaPattern.MatchString(p.Head.SHA)||p.Head.Ref!=g.RootBranch{
   return RootTipReport{},fmt.Errorf("ROOT_TIP_STALE_%d",g.RootPR)
  }
  cmp,err:=compare(ctx,mainSHA,p.Head.SHA)
  if err!=nil{return RootTipReport{},fmt.Errorf("ROOT_TIP_SOURCE_COMPARE_%d: %w",g.RootPR,err)}
  if cmp.AheadBy<0||cmp.BehindBy<0{
   return RootTipReport{},fmt.Errorf("ROOT_TIP_BAD_COMPARISON_%d",g.RootPR)
  }
  tip:=RootTip{PR:p.Number,HeadSHA:p.Head.SHA,MainSHA:mainSHA,
   Ahead:cmp.AheadBy,Behind:cmp.BehindBy,Divergence:cmp.Status,
   Action:"RETAIN_UNMERGED_UNTIL_EXACT_OWNER_AND_RIGHTS_REVIEW"}
  switch {
  case cmp.AheadBy==0&&(cmp.Status=="behind"||cmp.Status=="identical"):
   tip.Status="SOURCE_HEAD_REACHABLE_FROM_MAIN_REVIEW_ONLY"
   out.IntegratedAncestors++
  case cmp.Status=="ahead"&&cmp.BehindBy==0&&cmp.AheadBy>0:
   tip.Status="ROOT_HAS_UNMERGED_SOURCE_COMMITS"
   out.UnmergedSourceRoots++
  case cmp.Status=="diverged":
   tip.Status="ROOT_HISTORY_DIVERGED_REVIEW"
   out.Diverged++
  default:
   tip.Status="UNKNOWN_HISTORY_HOLD"
   out.OtherHeld++
  }
  out.Tips=append(out.Tips,tip)
 }
 sort.Slice(out.Tips,func(i,j int)bool{return out.Tips[i].PR<out.Tips[j].PR})
 out.RootTipsChecked=len(out.Tips)
 if out.RootTipsChecked!=out.IntegratedAncestors+out.UnmergedSourceRoots+out.Diverged+out.OtherHeld{
  return RootTipReport{},errors.New("ROOT_TIP_PARTITION_FAILED")
 }
 return out,nil
}
func(r RootTipReport)Markdown()string{
 var b strings.Builder
 fmt.Fprintf(&b,`# Independent root PR source reachability — read-only

Exact main: %s | root PRs: %d | leaf tips checked: %d | already reachable: %d | own unmerged commits: %d | history diverged: %d | unknown held: %d | mutations: **0**.

A source SHA already reachable from main is a **CANDIDATE** for owner review, not authorization to close, merge, delete, release, or discard custody. All other roots retain unmerged work. Stacked dependent PRs were not evaluated as independent tips.

`,r.MainSHA,r.RootCount,r.RootTipsChecked,r.IntegratedAncestors,r.UnmergedSourceRoots,r.Diverged,r.OtherHeld)
 b.WriteString(`| Root PR | Ahead | Behind | State | Disposition |
|---|---:|---:|---|---|
`)
 for _,t:=range r.Tips{
  fmt.Fprintf(&b,"| #%d | %d | %d | %s | %s |",t.PR,t.Ahead,t.Behind,t.Status,t.Action)
  b.WriteByte(10)
 }
 return b.String()
}
func(r RootTipReport)JSON()[]byte{
 v,_:=json.MarshalIndent(r,"","  ");return append(v,byte(10))
}
