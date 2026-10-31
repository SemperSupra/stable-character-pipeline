package scenejob

import(
 "bytes"
 "embed"
 "encoding/json"
 "errors"
 "io"
 "net/http"
 "net/url"
 "strings"
)
 //go:embed ui.html ui.js
var ui embed.FS

func parseJob(r io.Reader)(Request,error){
 var q Request
 b,err:=io.ReadAll(io.LimitReader(r,(1<<20)+1))
 if err!=nil||len(b)>(1<<20){return q,errors.New("REQUEST_OVERSIZED")}
 dec:=json.NewDecoder(bytes.NewReader(b))
 first,err:=dec.Token()
 if err!=nil||first!=json.Delim('{'){return q,errors.New("REQUEST_NOT_OBJECT")}
 seen:=map[string]bool{}
 for dec.More(){
  token,err:=dec.Token();if err!=nil{return q,err}
  key,ok:=token.(string)
  if !ok||seen[key]{return q,errors.New("REQUEST_DUPLICATE_KEY")}
  seen[key]=true
  if key!="schema"&&key!="job_id"&&key!="revision"&&key!="source_class"{
   return q,errors.New("REQUEST_UNKNOWN_FIELD")
  }
  var s string
  if err:=dec.Decode(&s);err!=nil{return q,err}
 }
 if _,err:=dec.Token();err!=nil{return q,err}
 if _,err:=dec.Token();err!=io.EOF{return q,errors.New("REQUEST_TRAILING_JSON")}
 strict:=json.NewDecoder(bytes.NewReader(b));strict.DisallowUnknownFields()
 if err:=strict.Decode(&q);err!=nil{return q,err}
 return q,nil
}
func acceptableOrigin(r *http.Request)bool{
 origin:=r.Header.Get("Origin")
 if origin==""{return true}
 u,err:=url.Parse(origin)
 if err!=nil||u.Scheme!="http"||!strings.EqualFold(u.Host,r.Host)||
  u.Path!=""||u.RawQuery!=""||u.Fragment!=""{return false}
 return true
}
func jsonResult(w http.ResponseWriter,code int,p any){
 w.Header().Set("Content-Type","application/json; charset=utf-8")
 w.Header().Set("Cache-Control","no-store")
 w.WriteHeader(code)
 _=json.NewEncoder(w).Encode(p)
}
func (m *Manager)Handler()http.Handler{
 mux:=http.NewServeMux()
 mux.HandleFunc("/v1/capabilities",func(w http.ResponseWriter,r *http.Request){
  if r.Method!="GET"{http.Error(w,"method",405);return}
  jsonResult(w,200,map[string]any{
   "schema":RequestSchema,"scope":"public-synthetic",
   "revision":m.revision,"human_ui":"/",
   "automation_cli":"scenejob run --revision <SHA> --output <OUT> --repo <SOURCE>",
   "agent_discovery":"/v1/capabilities",
   "agent_execute":"POST /v1/jobs","job_status":"GET /v1/jobs/"+JobID,
   "media":"GET /v1/jobs/"+JobID+"/media/{OriginalFront|OriginalOblique}",
   "scientific_acceptance":"FAIL_ABSTRACT_LIMBS_ONLY",
   "release":"HELD_R009_NOT_RUN_NOT_ADMITTED",
  })
 })
 mux.HandleFunc("/v1/jobs",func(w http.ResponseWriter,r *http.Request){
  if r.Method!="POST"{http.Error(w,"method",405);return}
  if r.Header.Get("Content-Type")!="application/json"{
   jsonResult(w,415,map[string]string{"status":"FAIL","code":"CONTENT_TYPE_REQUIRED"});return
  }
  if !acceptableOrigin(r){
   jsonResult(w,403,map[string]string{"status":"FAIL","code":"ORIGIN_REJECTED"});return
  }
  req,err:=parseJob(http.MaxBytesReader(w,r.Body,1<<20))
  if err!=nil{jsonResult(w,400,map[string]string{"status":"FAIL","code":"INVALID_WIRE_REQUEST"});return}
  if err:=Admit(req,m.revision);err!=nil{
   jsonResult(w,422,map[string]string{"status":"FAIL","code":"UNAUTHORIZED_JOB_OR_REVISION"});return
  }
  result,err:=m.Run(r.Context(),req)
  if err!=nil{
   jsonResult(w,503,map[string]string{"status":"FAIL","code":"SOURCE_SAFE_NATIVE_JOB_OR_RECEIPT_FAILED"});return
  }
  jsonResult(w,200,result)
 })
 mux.HandleFunc("/v1/jobs/"+JobID,func(w http.ResponseWriter,r *http.Request){
  if r.Method!="GET"{http.Error(w,"method",405);return}
  result,ok,err:=m.Result()
  if err!=nil{jsonResult(w,503,map[string]string{"status":"FAIL","code":"RECEIPT_MUTATED"});return}
  if !ok{jsonResult(w,404,map[string]string{"status":"UNKNOWN","code":"JOB_NOT_RUN"});return}
  jsonResult(w,200,result)
 })
 for _,camera:=range cameras{
  camera:=camera
  path:="/v1/jobs/"+JobID+"/media/"+camera
  mux.HandleFunc(path,func(w http.ResponseWriter,r *http.Request){
   if r.Method!="GET"&&r.Method!="HEAD"{http.Error(w,"method",405);return}
   filename,err:=m.MediaPath(camera)
   if err!=nil{http.Error(w,"job unavailable or tampered",404);return}
   w.Header().Set("Cache-Control","no-store")
   w.Header().Set("Content-Type","video/mp4")
   http.ServeFile(w,r,filename)
  })
 }
 mux.HandleFunc("/ui.js",func(w http.ResponseWriter,r *http.Request){
  if r.Method!="GET"{http.Error(w,"method",405);return}
  raw,err:=ui.ReadFile("ui.js");if err!=nil{http.Error(w,"no ui",500);return}
  w.Header().Set("Content-Type","text/javascript; charset=utf-8");_,_=w.Write(raw)
 })
 mux.HandleFunc("/",func(w http.ResponseWriter,r *http.Request){
  if r.URL.Path!="/"{http.NotFound(w,r);return}
  if r.Method!="GET"{http.Error(w,"method",405);return}
  raw,err:=ui.ReadFile("ui.html");if err!=nil{http.Error(w,"no ui",500);return}
  w.Header().Set("Content-Type","text/html; charset=utf-8");_,_=w.Write(raw)
 })
 return http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){
  w.Header().Set("X-Content-Type-Options","nosniff")
  w.Header().Set("Referrer-Policy","no-referrer")
  w.Header().Set("Cache-Control","no-store")
  w.Header().Set("Content-Security-Policy",
    "default-src 'none'; script-src 'self'; connect-src 'self'; style-src 'self'; "+
    "media-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
  mux.ServeHTTP(w,r)
 })
}
