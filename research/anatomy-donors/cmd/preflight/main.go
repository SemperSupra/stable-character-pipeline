package main

import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "net/http"
 "os"
 "os/exec"
 "regexp"
 "strings"
 "time"
)
type Source struct {
 Repo string `json:"repo"`
 Branch string `json:"branch"`
 Readme string `json:"readme"`
 License string `json:"license"`
}
type Digest struct {
 SHA256 string `json:"sha256,omitempty"`
 Bytes int `json:"bytes,omitempty"`
}
type Receipt struct {
 Repo string `json:"repo"`
 Branch string `json:"branch"`
 SourceSHA string `json:"source_sha,omitempty"`
 Readme Digest `json:"readme"`
 License Digest `json:"license"`
 Status string `json:"status"`
 Error string `json:"error,omitempty"`
 AssetRights string `json:"asset_rights"`
}
var sources=[]Source{
 {"opensim-org/opensim-core","main","README.md","LICENSE.txt"},
 {"MyoHub/myo_sim","main","README.md","LICENSE"},
 {"sofa-framework/sofa","master","README.md","LICENSE-LGPL.md"},
 {"febiosoftware/FEBio","develop","README.md","LICENSE"},
 {"artisynth/artisynth_core","master","README","LICENSE"},
 {"Z-Anatomy/Models-of-human-anatomy","master","Readme.md","License.txt"},
}
var shaRE=regexp.MustCompile(`^[a-f0-9]{40}$`)
func validateSources(list []Source)error{
 if len(list)==0{return errors.New("empty manifest")}
 seen:=map[string]bool{}
 for _,s:=range list{
  if seen[s.Repo]{return fmt.Errorf("duplicate %s",s.Repo)};seen[s.Repo]=true
  if strings.Contains(s.Repo,"..")||strings.Contains(s.Branch,"..")||strings.Count(s.Repo,"/")!=1||s.Branch==""||s.Readme==""||s.License==""{return fmt.Errorf("invalid source %s",s.Repo)}
 }
 return nil
}
func sourceSHA(ctx context.Context,s Source)(string,error){
 target:="https://github.com/"+s.Repo+".git"
 cmd:=exec.CommandContext(ctx,"git","ls-remote",target,"refs/heads/"+s.Branch)
 data,err:=cmd.Output();if err!=nil{return "",fmt.Errorf("ls-remote: %w",err)}
 parts:=strings.Fields(strings.TrimSpace(string(data)))
 if len(parts)!=2||!shaRE.MatchString(parts[0])||parts[1]!="refs/heads/"+s.Branch{sample:=strings.TrimSpace(string(data));if len(sample)>180{sample=sample[:180]};return "",fmt.Errorf("ambiguous or invalid Git ref: fields=%d observed=%q",len(parts),sample)}
 return parts[0],nil
}
func fetchDigest(ctx context.Context,client *http.Client,s Source,sha,path string)(Digest,error){
 url:="https://raw.githubusercontent.com/"+s.Repo+"/"+sha+"/"+path
 req,err:=http.NewRequestWithContext(ctx,"GET",url,nil);if err!=nil{return Digest{},err}
 rsp,err:=client.Do(req);if err!=nil{return Digest{},err}
 defer rsp.Body.Close()
 if rsp.StatusCode!=200{return Digest{},fmt.Errorf("source text HTTP %d",rsp.StatusCode)}
 data,err:=io.ReadAll(io.LimitReader(rsp.Body,1024*1024+1));if err!=nil{return Digest{},err}
 if len(data)==0||len(data)>1024*1024{return Digest{},errors.New("source document empty or exceeds 1MiB")}
 sum:=sha256.Sum256(data);return Digest{SHA256:hex.EncodeToString(sum[:]),Bytes:len(data)},nil
}
func probe(s Source)Receipt{
 r:=Receipt{Repo:s.Repo,Branch:s.Branch,Status:"UNKNOWN",AssetRights:"NOT_REVIEWED"}
 ctx,cancel:=context.WithTimeout(context.Background(),25*time.Second);defer cancel()
 sha,err:=sourceSHA(ctx,s);if err!=nil{r.Error=err.Error();return r}
 r.SourceSHA=sha
 client:=&http.Client{Timeout:12*time.Second}
 r.Readme,err=fetchDigest(ctx,client,s,sha,s.Readme);if err!=nil{r.Error="README: "+err.Error();return r}
 r.License,err=fetchDigest(ctx,client,s,sha,s.License);if err!=nil{r.Error="LICENSE: "+err.Error();return r}
 r.Status="SOURCE_TEXT_PINNED"
 return r
}
func main(){
 if err:=validateSources(sources);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 records:=make([]Receipt,0,len(sources));failures:=0
 for _,s:=range sources{r:=probe(s);records=append(records,r);if r.Status!="SOURCE_TEXT_PINNED"{failures++}}
 out:=map[string]any{"schema":"scp.anatomy.donor_source_preflight.v1","status":"SOURCE_METADATA_ONLY","failures":failures,"records":records,"rights_admitted":false,"runtime_qualified":false}
 encoder:=json.NewEncoder(os.Stdout);encoder.SetIndent("","  ");_ = encoder.Encode(out)
 if failures>0{os.Exit(1)}
}
