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
 "strings"
 "time"
)

const upstream = "8f492390ddc7a2ae221a1369ef560589cf8c70fb"
const prefix = "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/"+upstream+"/Models/AnimatedTriangle/"
const ua = "StableCharacterPipeline-Research/0.1 (+https://github.com/SemperSupra/stable-character-pipeline/issues/19)"
type Receipt struct {
 Schema string `json:"schema"`
 Provider string `json:"provider"`
 Action string `json:"action"`
 Language string `json:"language,omitempty"`
 Source string `json:"source"`
 Bytes int `json:"bytes"`
 SHA256 string `json:"sha256"`
 Candidates []string `json:"candidates,omitempty"`
 License string `json:"license,omitempty"`
 Rights string `json:"rights"`
 Claim string `json:"claim"`
}
func fetch(client *http.Client, rawURL string, maxBytes int64, allowedHost string)([]byte,error) {
 u,err:=url.Parse(rawURL)
 if err!=nil||u.Scheme!="https"||u.Hostname()!=allowedHost||u.User!=nil{return nil,errors.New("unapproved HTTPS host")}
 req,err:=http.NewRequest(http.MethodGet,rawURL,nil)
 if err!=nil{return nil,err}
 req.Header.Set("User-Agent",ua)
 resp,err:=client.Do(req)
 if err!=nil{return nil,err}
 defer resp.Body.Close()
 if resp.StatusCode!=200{return nil,fmt.Errorf("provider access HOLD status=%d",resp.StatusCode)}
 body,err:=io.ReadAll(io.LimitReader(resp.Body,maxBytes+1))
 if err!=nil{return nil,err}
 if int64(len(body))>maxBytes {return nil,errors.New("response exceeds hard sample bound")}
 return body,nil
}
func sha(b []byte)string{sum:=sha256.Sum256(b);return hex.EncodeToString(sum[:])}
func client()*http.Client{return &http.Client{Timeout:15*time.Second,CheckRedirect:func(_ *http.Request,_ []*http.Request)error{return http.ErrUseLastResponse}}}
func sample(out string)([]Receipt,error){
 // The upstream README explicitly identifies the author and CC0 status for this one sample.
 // Never broaden this admission to other models or datasets.
 os.MkdirAll(out,0755)
 cl:=client()
 items:=[]struct{name,url string;cap int64}{
  {"README.md",prefix+"README.md",12000},
  {"AnimatedTriangle.gltf",prefix+"glTF/AnimatedTriangle.gltf",10000},
  {"AnimatedTriangle_geometry.bin",prefix+"glTF/AnimatedTriangle_geometry.bin",512},
  {"AnimatedTriangle_animation.bin",prefix+"glTF/AnimatedTriangle_animation.bin",512},
 }
 var receipts []Receipt
 buffers:=map[string][]byte{}
 for index,item:=range items{
  if index>0 {time.Sleep(2100*time.Millisecond)}
  b,err:=fetch(cl,item.url,item.cap,"raw.githubusercontent.com")
  if err!=nil{return receipts,fmt.Errorf("%s: %w",item.name,err)}
  buffers[item.name]=b
  if err:=os.WriteFile(filepath.Join(out,item.name),b,0644);err!=nil{return receipts,err}
  receipts=append(receipts,Receipt{Schema:"scp.provider_actual_fixture.v1",Provider:"khronos-gltf-sample-assets",Action:"RIGHTS_CLEARED_SMALL_SAMPLE_DOWNLOAD",Source:item.url,Bytes:len(b),SHA256:sha(b),License:"CC0-1.0 for AnimatedTriangle per upstream README",Rights:"SAMPLE_ONLY",Claim:"actual byte-transfer evidence, not automatic production admission"})
 }
 if !strings.Contains(string(buffers["README.md"]),"Creative Commons Zero v1.0 Universal"){return receipts,errors.New("source author license declaration missing")}
 var gltf struct {
  Asset struct{ Version string `json:"version"`} `json:"asset"`
  Animations []json.RawMessage `json:"animations"`
  Buffers []struct{ URI string `json:"uri"`; Length int `json:"byteLength"`} `json:"buffers"`
 }
 if err:=json.Unmarshal(buffers["AnimatedTriangle.gltf"],&gltf);err!=nil{return receipts,err}
 if gltf.Asset.Version!="2.0"||len(gltf.Animations)<1||len(gltf.Buffers)!=2{return receipts,errors.New("wrong glTF fixture version/animation/buffer manifest")}
 expected:=map[string]int{"AnimatedTriangle_geometry.bin":44,"AnimatedTriangle_animation.bin":100}
 for _,decl:=range gltf.Buffers{
  want,ok:=expected[decl.URI]
  if !ok||decl.Length!=want||len(buffers[decl.URI])!=want{return receipts,errors.New("external dependency or byte length mismatch")}
 }
 return receipts,nil
}
func search()([]Receipt,error) {
 cl:=client();queries:=[]struct{language,term string}{
  {"en","walking"},{"de","gehen"},{"th","เดิน"},
 }
 rows:=[]Receipt{}
 for i,q:=range queries {
  if i>0{time.Sleep(2100*time.Millisecond)}
  u:="https://api.polyhaven.com/search?q="+url.QueryEscape(strings.ToLower(q.term))+"&t=models&limit=5"
  body,err:=fetch(cl,u,65536,"api.polyhaven.com")
  if err!=nil{return rows,fmt.Errorf("%s: %w",q.language,err)}
  var payload struct{Total int `json:"total"`;Results []struct{Slug string `json:"slug"`;Score float64 `json:"score"`} `json:"results"`}
  if err:=json.Unmarshal(body,&payload);err!=nil{return rows,err}
  if len(payload.Results)>5{return rows,errors.New("provider exceeded requested result count")}
  slugs:=make([]string,0,len(payload.Results))
  for _,entry:=range payload.Results{
   if entry.Slug=="" {return rows,errors.New("empty source asset slug")}
   slugs=append(slugs,entry.Slug)
  }
  rows=append(rows,Receipt{Schema:"scp.provider_actual_search.v1",Provider:"polyhaven",Action:"ANONYMOUS_LANGUAGE_RETRIEVAL",Language:q.language,Source:u,Bytes:len(body),SHA256:sha(body),Candidates:slugs,License:"live API ToS + individual CC0 assets",Rights:"METADATA_ONLY",Claim:"ranked retrieval observation, NOT CPE concept semantic truth or absence; Powered by Poly Haven"})
 }
 return rows,nil
}
func main(){
 lane:=flag.String("lane","","sample or search")
 out:=flag.String("out","reports","Artifact directory")
 flag.Parse()
 if err:=os.MkdirAll(*out,0755);err!=nil{panic(err)}
 var result []Receipt;var err error
 switch *lane{case "sample":result,err=sample(*out);case "search":result,err=search();default:fmt.Fprintln(os.Stderr,"invalid lane");os.Exit(2)}
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 b,err:=json.MarshalIndent(result,"","  ")
 if err!=nil{panic(err)}
 b=append(b,'\n')
 if err:=os.WriteFile(filepath.Join(*out,"receipt-"+*lane+".json"),b,0644);err!=nil{panic(err)}
 fmt.Print(string(b))
}
