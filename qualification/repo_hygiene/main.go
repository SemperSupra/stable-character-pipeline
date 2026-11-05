// SPDX-License-Identifier: MIT
// Public-original synthetic Stable Character Pipeline repo hygiene auditor.
// Read-only GitHub GETs. Apply writes ONLY a local JSON receipt; never merges,
// closes issues/PRs, deletes branches, or publishes any private source.
package main

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "net/http"
 "net/url"
 "os"
 "path/filepath"
 "sort"
 "strings"
 "time"
)

type Scope struct {
 Schema string `json:"schema"`
 Repository string `json:"repository"`
 PRs []int `json:"prs"`
}
type PR struct {
 Number int `json:"number"`
 State string `json:"state"`
 Draft bool `json:"draft"`
 Merged bool `json:"merged"`
 Mergeable *bool `json:"mergeable"`
 Head struct{ Ref string `json:"ref"`; SHA string `json:"sha"` } `json:"head"`
 Base struct{ Ref string `json:"ref"`; SHA string `json:"sha"` } `json:"base"`
}
type PRFile struct{ Filename string `json:"filename"`; Status string `json:"status"` }
type WorkflowRuns struct{ TotalCount int `json:"total_count"`; Runs []struct{
 ID int64 `json:"id"`; HeadSHA string `json:"head_sha"`
 Status string `json:"status"`; Conclusion string `json:"conclusion"`
 HTMLURL string `json:"html_url"`
} `json:"workflow_runs"` }
type Record struct {
 Number int `json:"number"`
 State string `json:"state"`
 Draft bool `json:"draft"`
 Merged bool `json:"merged"`
 HeadBranch string `json:"head_branch"`
 HeadSHA string `json:"head_sha"`
 BaseBranch string `json:"base_branch"`
 BaseSHA string `json:"base_sha"`
 BasePR int `json:"base_pr,omitempty"`
 BaseHeadCurrent string `json:"base_head_current,omitempty"`
 BaseDrift bool `json:"base_drift"`
 Paths []string `json:"changed_paths"`
 CI string `json:"exact_head_ci"`
 CIRunID int64 `json:"exact_head_ci_run_id,omitempty"`
 Disposition string `json:"disposition"`
 NoAutoPromotion bool `json:"no_auto_promotion"`
}
type Overlap struct{
 Left int `json:"left"`; Right int `json:"right"`
 Paths []string `json:"paths"`
 Kind string `json:"kind"`
}
type Summary struct{
 Total int `json:"total"`
 OpenDraft int `json:"open_draft"`
 ClosedUnmerged int `json:"closed_unmerged"`
 Merged int `json:"merged"`
 DriftedBases int `json:"drifted_bases"`
 ExactHeadGreen int `json:"exact_head_green"`
 CIUnknownOrFail int `json:"ci_unknown_or_fail"`
 IndependentCollisions int `json:"independent_collisions"`
 ExpectedStackOverlaps int `json:"expected_stack_overlaps"`
}
type Receipt struct {
 Schema string `json:"schema"`
 Repository string `json:"repository"`
 Source string `json:"source"`
 ReadOnlyRemote bool `json:"read_only_remote"`
 AutomaticMerges int `json:"automatic_merges"`
 AutomaticClosures int `json:"automatic_closures"`
 AutomaticBranchDeletes int `json:"automatic_branch_deletes"`
 PRs []Record `json:"prs"`
 Overlaps []Overlap `json:"overlaps"`
 Summary Summary `json:"summary"`
 Digest string `json:"digest"`
}
type Getter func(string,any)error

func githubGetter(repo, token string)Getter{
 client:=&http.Client{Timeout:25*time.Second}
 prefix:="https://api.github.com/repos/"+repo+"/"
 return func(path string,dst any)error{
  req,e:=http.NewRequest(http.MethodGet,prefix+path,nil);if e!=nil{return e}
  req.Header.Set("Accept","application/vnd.github+json")
  req.Header.Set("X-GitHub-Api-Version","2022-11-28")
  req.Header.Set("User-Agent","scp-hygiene-audit-readonly-v1")
  if token!=""{req.Header.Set("Authorization","Bearer "+token)}
  resp,e:=client.Do(req);if e!=nil{return e};defer resp.Body.Close()
  if resp.StatusCode!=200{return fmt.Errorf("GitHub read %s status=%d",path,resp.StatusCode)}
  return json.NewDecoder(io.LimitReader(resp.Body,2<<20)).Decode(dst)
 }
}
func validSHA(s string)bool{
 if len(s)!=40{return false}
 for _,c:=range s{if !strings.ContainsRune("0123456789abcdef",c){return false}}
 return true
}
func validateScope(s Scope)error{
 if s.Schema!="scp.repo_hygiene_scope.v1"{return errors.New("scope schema mismatch")}
 if s.Repository!="SemperSupra/stable-character-pipeline"{return errors.New("repository outside public synthetic scope")}
 if len(s.PRs)==0||len(s.PRs)>40{return errors.New("PR list count invalid")}
 seen:=map[int]bool{}
 for _,n:=range s.PRs{
  if n<=0||n>1000000||seen[n]{return errors.New("invalid or duplicate PR number")}
  seen[n]=true
 }
 return nil
}
func readScope(path string)(Scope,error){
 var s Scope
 f,e:=os.Open(path);if e!=nil{return s,e};defer f.Close()
 d:=json.NewDecoder(io.LimitReader(f,1<<20));d.DisallowUnknownFields()
 if e=d.Decode(&s);e!=nil{return s,e}
 if e=d.Decode(new(any));e!=io.EOF{return s,errors.New("trailing scope JSON")}
 return s,validateScope(s)
}
func stateDisposition(p PR)string{
 if p.Merged{return "MERGED_RETAIN_PROVENANCE_UNVERIFIED_ACCEPTANCE"}
 if p.State=="closed"{return "CLOSED_UNMERGED_RETAIN_FIRST_FAILURES"}
 if p.Draft{return "OPEN_DRAFT_RETAIN_OWNER_GATES"}
 return "OPEN_OWNER_REVIEW_REQUIRED_NO_AUTO_MERGE"
}
func ciFor(get Getter,branch,sha string)(string,int64,error){
 var runs WorkflowRuns
 path:="actions/runs?branch="+url.QueryEscape(branch)+"&per_page=100"
 if e:=get(path,&runs);e!=nil{return "UNKNOWN_READ_ERROR",0,e}
 for _,r:=range runs.Runs{
  if r.HeadSHA!=sha{continue}
  if r.Status!="completed"{return "EXACT_HEAD_"+strings.ToUpper(r.Status),r.ID,nil}
  if r.Conclusion=="success"{return "EXACT_HEAD_WORKFLOW_SUCCESS_NOT_OWNER_ACCEPTANCE",r.ID,nil}
  return "EXACT_HEAD_"+strings.ToUpper(r.Conclusion),r.ID,nil
 }
 return "UNKNOWN_NO_EXACT_HEAD_RUN_IN_FIRST_PAGE",0,nil
}
func fileList(get Getter,n int)([]string,error){
 paths:=[]string{}
 seen:=map[string]bool{}
 for page:=1;page<=10;page++{
  var f []PRFile
  if e:=get(fmt.Sprintf("pulls/%d/files?per_page=100&page=%d",n,page),&f);e!=nil{return nil,e}
  for _,v:=range f{
   if v.Filename==""||seen[v.Filename]{return nil,fmt.Errorf("empty or duplicate PR#%d file path",n)}
   if len(v.Filename)>4096{return nil,errors.New("file path too long")}
   seen[v.Filename]=true;paths=append(paths,v.Filename)
  }
  if len(f)<100{sort.Strings(paths);return paths,nil}
 }
 return nil,errors.New("file pagination cap reached: fail closed")
}
func isAncestor(a,b int,byNum map[int]Record)bool{
 seen:=map[int]bool{}
 for current:=b;current>0&&!seen[current];{
  seen[current]=true
  r,ok:=byNum[current];if !ok{return false}
  if r.BasePR==a{return true}
  current=r.BasePR
 }
 return false
}
func build(s Scope,get Getter)(Receipt,error){
 if e:=validateScope(s);e!=nil{return Receipt{},e}
 out:=Receipt{Schema:"scp.repo_hygiene_receipt.v1",Repository:s.Repository,Source:"GitHub_PUBLIC_READONLY",ReadOnlyRemote:true}
 numbers:=append([]int(nil),s.PRs...);sort.Ints(numbers)
 byNum:=map[int]Record{}
 byBranch:=map[string]int{}
 for _,n:=range numbers{
  var p PR
  if e:=get(fmt.Sprintf("pulls/%d",n),&p);e!=nil{return Receipt{},e}
  if p.Number!=n||!validSHA(p.Head.SHA)||!validSHA(p.Base.SHA)||p.Head.Ref==""||p.Base.Ref==""{
   return Receipt{},fmt.Errorf("PR#%d invalid GitHub source fields",n)
  }
  if _,dup:=byBranch[p.Head.Ref];dup{return Receipt{},errors.New("duplicate PR head branch in scope")}
  byBranch[p.Head.Ref]=n
  paths,e:=fileList(get,n);if e!=nil{return Receipt{},e}
  ci,run,e:=ciFor(get,p.Head.Ref,p.Head.SHA);if e!=nil{return Receipt{},e}
  byNum[n]=Record{
   Number:n,State:p.State,Draft:p.Draft,Merged:p.Merged,
   HeadBranch:p.Head.Ref,HeadSHA:p.Head.SHA,BaseBranch:p.Base.Ref,BaseSHA:p.Base.SHA,
   Paths:paths,CI:ci,CIRunID:run,Disposition:stateDisposition(p),NoAutoPromotion:true,
  }
 }
 for _,n:=range numbers{
  r:=byNum[n]
  if parent,ok:=byBranch[r.BaseBranch];ok{
   r.BasePR=parent
   r.BaseHeadCurrent=byNum[parent].HeadSHA
   r.BaseDrift=r.BaseSHA!=r.BaseHeadCurrent
   if r.BaseDrift{r.Disposition="BLOCK_BASE_HEAD_DRIFT_OWNER_REVIEW"}
  }
  byNum[n]=r
  out.PRs=append(out.PRs,r)
  if r.State=="open"&&r.Draft{out.Summary.OpenDraft++}
  if r.State=="closed"&&!r.Merged{out.Summary.ClosedUnmerged++}
  if r.Merged{out.Summary.Merged++}
  if r.BaseDrift{out.Summary.DriftedBases++}
  if r.CI=="EXACT_HEAD_WORKFLOW_SUCCESS_NOT_OWNER_ACCEPTANCE"{out.Summary.ExactHeadGreen++}else{out.Summary.CIUnknownOrFail++}
 }
 for i:=0;i<len(numbers);i++{for j:=i+1;j<len(numbers);j++{
  a,b:=byNum[numbers[i]],byNum[numbers[j]]
  pathsA:=map[string]bool{};for _,p:=range a.Paths{pathsA[p]=true}
  common:=[]string{};for _,p:=range b.Paths{if pathsA[p]{common=append(common,p)}}
  if len(common)==0{continue}
  kind:="INDEPENDENT_PATH_COLLISION_REQUIRES_REVIEW"
  if isAncestor(a.Number,b.Number,byNum)||isAncestor(b.Number,a.Number,byNum){
   kind="EXPECTED_STACK_INHERITANCE"
   out.Summary.ExpectedStackOverlaps++
  }else{out.Summary.IndependentCollisions++}
  out.Overlaps=append(out.Overlaps,Overlap{Left:a.Number,Right:b.Number,Paths:common,Kind:kind})
 }}
 out.Summary.Total=len(out.PRs)
 if e:=seal(&out);e!=nil{return Receipt{},e}
 return out,nil
}
func seal(r *Receipt)error{
 r.Digest=""
 wire,e:=json.Marshal(r);if e!=nil{return e}
 h:=sha256.Sum256(wire);r.Digest=hex.EncodeToString(h[:]);return nil
}
func verify(r Receipt)error{
 if r.Schema!="scp.repo_hygiene_receipt.v1"||r.Repository!="SemperSupra/stable-character-pipeline"||
  !r.ReadOnlyRemote||r.AutomaticMerges!=0||r.AutomaticClosures!=0||r.AutomaticBranchDeletes!=0{
  return errors.New("unsafe or malformed receipt")
 }
 digest:=r.Digest;if len(digest)!=64{return errors.New("missing digest")}
 if e:=seal(&r);e!=nil{return e}
 if r.Digest!=digest{return errors.New("receipt hash mismatch")}
 if r.Summary.Total!=len(r.PRs){return errors.New("inconsistent PR count")}
 for i,p:=range r.PRs{
  if p.Number<=0||!p.NoAutoPromotion||!validSHA(p.HeadSHA)||!validSHA(p.BaseSHA){return errors.New("unverified PR record")}
  if i>0&&r.PRs[i-1].Number>=p.Number{return errors.New("PR order changed")}
 }
 return nil
}
func main(){
 mode:=flag.String("mode","plan","plan, apply, or verify")
 scopePath:=flag.String("scope","scope.json","explicit public-repo scope")
 output:=flag.String("out","hygiene-receipt.json","local receipt path")
 flag.Parse()
 if *mode=="verify"{
  raw,e:=os.ReadFile(*output);if e!=nil{fatal(e)}
  var r Receipt;if e=json.Unmarshal(raw,&r);e!=nil{fatal(e)}
  if e=verify(r);e!=nil{fatal(e)}
  fmt.Printf("RECEIPT_VERIFIED sha256=%s prs=%d collisions=%d drift=%d (source may have advanced)\n",r.Digest,r.Summary.Total,r.Summary.IndependentCollisions,r.Summary.DriftedBases)
  return
 }
 if *mode!="plan"&&*mode!="apply"{fatal(errors.New("unsupported mode"))}
 s,e:=readScope(*scopePath);if e!=nil{fatal(e)}
 r,e:=build(s,githubGetter(s.Repository,os.Getenv("GITHUB_TOKEN")));if e!=nil{fatal(e)}
 wire,e:=json.MarshalIndent(r,"","  ");if e!=nil{fatal(e)}
 wire=append(wire,'\n')
 if *mode=="plan"{os.Stdout.Write(wire);return}
 if e=os.MkdirAll(filepath.Dir(*output),0750);e!=nil{fatal(e)}
 temp,e:=os.CreateTemp(filepath.Dir(*output),".scp-hygiene-*");if e!=nil{fatal(e)}
 defer os.Remove(temp.Name())
 if _,e=temp.Write(wire);e!=nil{fatal(e)}
 if e=temp.Close();e!=nil{fatal(e)}
 if e=os.Rename(temp.Name(),*output);e!=nil{fatal(e)}
 check,e:=os.ReadFile(*output);if e!=nil{fatal(e)}
 var saved Receipt;if e=json.Unmarshal(check,&saved);e!=nil{fatal(e)}
 if e=verify(saved);e!=nil{fatal(e)}
 fmt.Printf("APPLIED_LOCAL_RECEIPT sha256=%s prs=%d collision=%d drift=%d\n",saved.Digest,saved.Summary.Total,saved.Summary.IndependentCollisions,saved.Summary.DriftedBases)
}
func fatal(e error){fmt.Fprintln(os.Stderr,"HARD_FAIL:",e);os.Exit(2)}
