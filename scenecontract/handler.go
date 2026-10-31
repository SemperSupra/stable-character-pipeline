package scenecontract
import(
 "embed"
 "encoding/json"
 "net/http"
 "net/url"
 "strings"
)
 //go:embed ui.html ui.js
var assets embed.FS
func send(w http.ResponseWriter,code int,d Decision){
 w.Header().Set("Content-Type","application/json; charset=utf-8")
 w.Header().Set("Cache-Control","no-store")
 w.WriteHeader(code)
 _=json.NewEncoder(w).Encode(d)
}
func Handler()http.Handler{
 mux:=http.NewServeMux()
 mux.HandleFunc("/v1/scenes/validate",func(w http.ResponseWriter,r *http.Request){
  if r.Method!=http.MethodPost{http.Error(w,"method not allowed",http.StatusMethodNotAllowed);return}
  if ct:=r.Header.Get("Content-Type");ct!="application/json"{send(w,415,Decision{Status:"FAIL",Code:"CONTENT_TYPE_REQUIRED"});return}
  if o:=r.Header.Get("Origin");o!=""{
   u,err:=url.Parse(o)
   if err!=nil||u.Scheme!="http"||!strings.EqualFold(u.Host,r.Host)||u.Path!=""{send(w,403,Decision{Status:"FAIL",Code:"ORIGIN_REJECTED"});return}
  }
  r.Body=http.MaxBytesReader(w,r.Body,1<<20)
  d,err:=Evaluate(r.Body)
  if err!=nil{send(w,400,d);return}
  if d.Status=="FAIL"{send(w,422,d);return}
  send(w,200,d)
 })
 mux.HandleFunc("/v1/capabilities",func(w http.ResponseWriter,r *http.Request){
  if r.Method!=http.MethodGet{http.Error(w,"method not allowed",405);return}
  w.Header().Set("Content-Type","application/json; charset=utf-8")
  w.Header().Set("Cache-Control","no-store")
  _,_=w.Write([]byte(`{"schema":"scp.scene.v1","human_ui":"/","automation_http":"/v1/scenes/validate","agent_discovery":"/v1/capabilities","status":"STRUCTURAL_REFERENCE_ONLY"}`))
 })
 mux.HandleFunc("/ui.js",func(w http.ResponseWriter,r *http.Request){
  if r.Method!=http.MethodGet{http.Error(w,"method not allowed",405);return}
  w.Header().Set("Content-Type","text/javascript; charset=utf-8")
  b,_:=assets.ReadFile("ui.js");_,_=w.Write(b)
 })
 mux.HandleFunc("/",func(w http.ResponseWriter,r *http.Request){
  if r.URL.Path!="/" {http.NotFound(w,r);return}
  if r.Method!=http.MethodGet{http.Error(w,"method not allowed",405);return}
  w.Header().Set("Content-Type","text/html; charset=utf-8")
  b,_:=assets.ReadFile("ui.html");_,_=w.Write(b)
 })
 return http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){
  w.Header().Set("X-Content-Type-Options","nosniff")
  w.Header().Set("Referrer-Policy","no-referrer")
  w.Header().Set("Content-Security-Policy","default-src 'none'; script-src 'self'; connect-src 'self'; style-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
  mux.ServeHTTP(w,r)
 })
}
