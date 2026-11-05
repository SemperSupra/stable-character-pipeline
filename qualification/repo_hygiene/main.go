// scp-hygiene is a READ-ONLY, fail-closed public repository PR reconciliation auditor.
// It NEVER merges, closes, changes branches, or deletes resources. Stdlib only.
package main

import (
 "context"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "net/http"
 "os"
 "path/filepath"
 "regexp"
 "sort"
 "strconv"
 "strings"
 "time"
)

const allowedRepo = "SemperSupra/stable-character-pipeline"
const schema = "scp.r009.repo_hygiene_snapshot.v1"

type CommitRef struct { Ref string `json:"ref"`; SHA string `json:"sha"` }
type Pull struct {
 Number int `json:"number"`
 Title string `json:"title"`
 State string `json:"state"`
 Draft bool `json:"draft"`
 UpdatedAt time.Time `json:"updated_at"`
 Head CommitRef `json:"head"`
 Base CommitRef `json:"base"`
 MergedAt *time.Time `json:"merged_at"`
 HTMLURL string `json:"html_url"`
}
type Snapshot struct {
 Schema string `json:"schema"`
 Repo string `json:"repo"`
 AsOf string `json:"as_of"`
 Complete bool `json:"complete"`
 FetchPages int `json:"fetch_pages"`
 PRs []Pull `json:"prs"`
}
type Item struct {
 Number int `json:"number"`
 Head string `json:"head"`
 Base string `json:"base"`
 Draft bool `json:"draft"`
 AgeDays int `json:"age_days"`
 Classification []string `json:"classification"`
 Hold []string `json:"hold"`
 Action string `json:"action"`
 URL string `json:"url"`
}
type Report struct {
 Schema string `json:"schema"`
 Repo string `json:"repo"`
 AsOf string `json:"as_of"`
 Complete bool `json:"complete"`
 PRsScanned int `json:"prs_scanned"`
 Findings []Item `json:"findings"`
 Recommendation string `json:"recommendation"`
 Mutations int `json:"mutations"`
 Stats map[string]int `json:"stats"`
}

func audit(s Snapshot, staleDays int) (Report,error) {
 if s.Schema != schema || s.Repo != allowedRepo {return Report{},errors.New("INVALID_SCHEMA_OR_REPO")}
 asOf,err:=time.Parse("2006-01-02",s.AsOf);if err!=nil{return Report{},fmt.Errorf("INVALID_AS_OF: %w",err)}
 if staleDays < 1{return Report{},errors.New("INVALID_STALE_DAYS")}
 heads:=map[string]int{}
 headSHA:=map[string][]int{}
 numbers:=map[int]bool{}
 for _,p:=range s.PRs {
  if p.Number<=0||numbers[p.Number]||p.State!="open"||p.MergedAt!=nil||len(p.Head.SHA)!=40||len(p.Base.SHA)!=40||p.Head.Ref==""||p.Base.Ref==""{return Report{},fmt.Errorf("INVALID_PR:%d",p.Number)}
  if p.HTMLURL!="" && !strings.HasPrefix(p.HTMLURL,"https://github.com/"+allowedRepo+"/pull/"){return Report{},fmt.Errorf("UNTRUSTED_URL:%d",p.Number)}
  numbers[p.Number]=true; heads[p.Head.Ref]=p.Number;headSHA[p.Head.SHA]=append(headSHA[p.Head.SHA],p.Number)
 }
 report:=Report{Schema:"scp.r009.repo_hygiene_report.v1",Repo:s.Repo,AsOf:s.AsOf,Complete:s.Complete,PRsScanned:len(s.PRs),Mutations:0,Recommendation:"OBSERVE/PLAN ONLY: owner authorization and independent rights, exact-source, custody, CI and scientific gates required before any merge, close or branch deletion"}
 for _,p:=range s.PRs {
  age:=int(asOf.Sub(p.UpdatedAt).Hours()/24);if age<0{age=0}
  tags:=[]string{};holds:=[]string{"OWNER_MERGE_CLOSE_APPROVAL_NOT_RECORDED","RIGHTS_CUSTODY_CI_AND_SCIENTIFIC_STATUS_NOT_VERIFIED"}
  if p.Draft {tags=append(tags,"DRAFT_RETAIN")}else{tags=append(tags,"READY_FOR_REVIEW_NOT_AUTOMERGE")}
  if p.Base.Ref!="main" && p.Base.Ref!="master" {
   if id,ok:=heads[p.Base.Ref];ok {tags=append(tags,fmt.Sprintf("OPEN_PARENT_PR_%d",id));holds=append(holds,"STACKED_PARENT_UNMERGED")
   } else {tags=append(tags,"NONDEFAULT_BASE_NO_OPEN_PARENT_IN_SNAPSHOT");holds=append(holds,"BASE_LINEAGE_NEEDS_RECONCILIATION")}
  } else {tags=append(tags,"DEFAULT_BRANCH_BASE")}
  if len(headSHA[p.Head.SHA])>1 {tags=append(tags,"SHARED_HEAD_COMMIT_REVIEW");holds=append(holds,"DUPLICATE_HEAD_NOT_PROVEN_REDUNDANT")}
  if age>=staleDays {tags=append(tags,"STALE_REVIEW_CANDIDATE");holds=append(holds,"STALE_DOES_NOT_IMPLY_SAFE_TO_CLOSE")}
  if !s.Complete {holds=append(holds,"INCOMPLETE_SNAPSHOT_NO_DISPOSITION")}
  sort.Strings(tags);sort.Strings(holds)
  report.Findings=append(report.Findings,Item{Number:p.Number,Head:p.Head.Ref,Base:p.Base.Ref,Draft:p.Draft,AgeDays:age,Classification:tags,Hold:holds,Action:"RETAIN_AND_REVIEW",URL:p.HTMLURL})
 }
 sort.Slice(report.Findings,func(i,j int)bool{return report.Findings[i].Number>report.Findings[j].Number})
 report.Stats=map[string]int{"total":len(report.Findings),"draft":0,"stacked_active":0,"nondefault_missing_parent":0,"stale_review":0,"shared_head":0,"default_base":0}
 for _,p:=range report.Findings {
  if p.Draft{report.Stats["draft"]++}
  for _,status:=range p.Classification {
   switch {
   case strings.HasPrefix(status,"OPEN_PARENT_PR_"):report.Stats["stacked_active"]++
   case status=="NONDEFAULT_BASE_NO_OPEN_PARENT_IN_SNAPSHOT":report.Stats["nondefault_missing_parent"]++
   case status=="STALE_REVIEW_CANDIDATE":report.Stats["stale_review"]++
   case status=="SHARED_HEAD_COMMIT_REVIEW":report.Stats["shared_head"]++
   case status=="DEFAULT_BRANCH_BASE":report.Stats["default_base"]++
   }
  }
 }

 return report,nil
}

func fetch(ctx context.Context, repo string, token string, day string, maxPages int) (Snapshot,error){
 if repo!=allowedRepo{return Snapshot{},errors.New("NOT_PUBLIC_ALLOWED_REPOSITORY")}
 if maxPages<1||maxPages>20{return Snapshot{},errors.New("INVALID_PAGE_LIMIT")}
 if token==""{return Snapshot{},errors.New("MISSING_READ_ONLY_GITHUB_TOKEN")}
 client:=&http.Client{Timeout:15*time.Second}
 snap:=Snapshot{Schema:schema,Repo:repo,AsOf:day}
 for page:=1;page<=maxPages;page++{
  path:="https://api.github.com/repos/"+repo+"/pulls?state=open&per_page=100&page="+strconv.Itoa(page)
  req,err:=http.NewRequestWithContext(ctx,"GET",path,nil);if err!=nil{return Snapshot{},err}
  req.Header.Set("Accept","application/vnd.github+json")
  req.Header.Set("Authorization","Bearer "+token)
  req.Header.Set("X-GitHub-Api-Version","2022-11-28")
  response,err:=client.Do(req);if err!=nil{return Snapshot{},err}
  if response.StatusCode!=200 {io.Copy(io.Discard,io.LimitReader(response.Body,2048));response.Body.Close();return Snapshot{},fmt.Errorf("GITHUB_HTTP_%d",response.StatusCode)}
  var rows []Pull
  err=json.NewDecoder(io.LimitReader(response.Body,5<<20)).Decode(&rows)
  response.Body.Close()
  if err!=nil{return Snapshot{},err}
  snap.FetchPages=page;snap.PRs=append(snap.PRs,rows...)
  if len(rows)<100{snap.Complete=true;break}
 }
 if !snap.Complete{return Snapshot{},errors.New("PAGINATION_INCOMPLETE_REFUSE_EXHAUSTIVE_CLASSIFICATION")}
 return snap,nil
}
func renderMD(r Report) string {
 var b strings.Builder
 fmt.Fprintf(&b,"# R009 public repository hygiene audit\n\nSource: `%s` | As of: %s | PRs: %d | Complete: %t | Mutations: %d\n\n",r.Repo,r.AsOf,r.PRsScanned,r.Complete,r.Mutations)
 b.WriteString("**No merges, closes, deletes, branch resets or releases were performed.** All entries default to `RETAIN_AND_REVIEW`. Classification does not waive owner rights, CI, scientific or custody holds.\n\n")
 fmt.Fprintf(&b,"Summary: **%d open** | **%d draft** | **%d stacked-active** | **%d nondefault bases without open parent** | **%d stale-review** | **%d shared head** | **%d main-based**. All are review-only classifications.\n\n",
 r.Stats["total"],r.Stats["draft"],r.Stats["stacked_active"],r.Stats["nondefault_missing_parent"],r.Stats["stale_review"],r.Stats["shared_head"],r.Stats["default_base"])

 b.WriteString("| PR | Branch base | State | Classification |\n|---|---|---|---|\n")
 safe:=regexp.MustCompile(`[^a-zA-Z0-9_./-]`)
 for _,x:=range r.Findings{
  base:=safe.ReplaceAllString(x.Base,"?")
  fmt.Fprintf(&b,"| #%d | `%s` | %s | %s |\n",x.Number,base,map[bool]string{true:"draft",false:"review"}[x.Draft],strings.Join(x.Classification,"; "))
 }
 return b.String()
}
func writeNew(path string,content []byte)error{
 if err:=os.MkdirAll(filepath.Dir(path),0700);err!=nil{return err}
 f,err:=os.OpenFile(path,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600);if err!=nil{return err}
 defer f.Close()
 _,err=f.Write(content);return err
}
func main(){
 var snapshotPath,repo,asOf,out string;var stale,maxPages int
 flag.StringVar(&snapshotPath,"snapshot","","offline snapshot input JSON (optional; absent means read-only API)")
 flag.StringVar(&repo,"repo",allowedRepo,"public repository exact allowlist")
 flag.StringVar(&asOf,"as-of","","YYYY-MM-DD UTC, required")
 flag.StringVar(&out,"out","","new output directory (required, must not exist)")
 flag.IntVar(&stale,"stale-days",14,"review threshold only; never closes")
 flag.IntVar(&maxPages,"max-pages",10,"fail closed when >max pages of 100")
 flag.Parse()
 if repo!=allowedRepo||out==""||asOf==""{fmt.Fprintln(os.Stderr,"INVALID_ARGS_OR_REPO");os.Exit(2)}
 if _,err:=time.Parse("2006-01-02",asOf);err!=nil{fmt.Fprintln(os.Stderr,"INVALID_AS_OF");os.Exit(2)}
 if _,err:=os.Stat(out);err==nil{fmt.Fprintln(os.Stderr,"REFUSE_OVERWRITE_OUTPUT_DIR");os.Exit(2)}else if !errors.Is(err,os.ErrNotExist){fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 var snap Snapshot;var err error
 if snapshotPath!=""{
  raw,e:=os.ReadFile(snapshotPath);if e!=nil{err=e}else{err=json.Unmarshal(raw,&snap)}
  if err==nil && (snap.AsOf!=asOf||snap.Repo!=repo){err=errors.New("SNAPSHOT_DATE_OR_REPO_MISMATCH")}
 }else{snap,err=fetch(context.Background(),repo,os.Getenv("GH_TOKEN"),asOf,maxPages)}
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 r,err:=audit(snap,stale);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 original,e1:=json.MarshalIndent(snap,"","  "); report,e2:=json.MarshalIndent(r,"","  ")
 if e1!=nil||e2!=nil {fmt.Fprintln(os.Stderr,"JSON_MARSHAL_FAILED");os.Exit(1)}
 if err=os.Mkdir(out,0700);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 for _,f:=range []struct{name string; data []byte}{{"snapshot.json",append(original,'\n')},{"report.json",append(report,'\n')},{"audit.md",[]byte(renderMD(r))}} {
  if err=writeNew(filepath.Join(out,f.name),f.data);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 }
 fmt.Printf("AUDIT_OK repo=%s PRs=%d draft=%d stacked=%d needs_lineage=%d stale=%d complete=%t mutations=0 output=%s\n",repo,r.PRsScanned,r.Stats["draft"],r.Stats["stacked_active"],r.Stats["nondefault_missing_parent"],r.Stats["stale_review"],r.Complete,out)
}
