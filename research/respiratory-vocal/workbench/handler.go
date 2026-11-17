// Package workbench provides a localhost-only *synthetic* respiratory sound
// catalog and a strict capability-gated audio API. The same source-derived
// action/fixture mapping drives novice humans, AT, automation and agents.
// This is not the private Physical Vocal engine or a calibrated voice model.
package workbench

import(
 "crypto/sha256"
 "embed"
 "encoding/json"
 "errors"
 "fmt"
 "net"
 "net/http"
 "strconv"
 "strings"

 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/behavior"
 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/capability"
 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/preview"
)

//go:embed index.html
var pages embed.FS

type ErrorReceipt struct{
 Schema string `json:"schema"`
 Code string `json:"code"`
 Message string `json:"message"`
 Action string `json:"action,omitempty"`
}
func errorJSON(w http.ResponseWriter,status int,code,message,action string){
 w.Header().Set("Content-Type","application/json; charset=utf-8")
 w.WriteHeader(status)
 _=json.NewEncoder(w).Encode(ErrorReceipt{Schema:"respiratory.workbench_error.v0",Code:code,Message:message,Action:action})
}
func common(w http.ResponseWriter){
 w.Header().Set("Cache-Control","no-store")
 w.Header().Set("X-Content-Type-Options","nosniff")
 w.Header().Set("Referrer-Policy","no-referrer")
 w.Header().Set("X-Research-Validity","original-synthetic-not-human-voice-or-physiology")
 w.Header().Set("Access-Control-Allow-Credentials","false")
}
func exactString(values map[string][]string,key string)(string,error){
 v,ok:=values[key]
 if !ok||len(v)!=1||v[0]==""||len(v[0])>80{return "",fmt.Errorf("exactly one bounded %s required",key)}
 return v[0],nil
}
func validScenario(names []string,name string)bool{
 for _,n:=range names{if n==name{return true}}
 return false
}
func Handler()http.Handler{
 mux:=http.NewServeMux()
 mux.HandleFunc("/",func(w http.ResponseWriter,r *http.Request){
  if r.URL.Path!="/"{errorJSON(w,404,"not_found","unknown route","");return}
  if r.URL.RawQuery!=""{errorJSON(w,400,"invalid_query","UI does not accept query parameters","");return}
  w.Header().Set("Content-Type","text/html; charset=utf-8")
  w.Header().Set("Content-Security-Policy","default-src 'none'; connect-src 'self'; media-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
  b,err:=pages.ReadFile("index.html")
  if err!=nil{errorJSON(w,500,"missing_page","local preview unavailable","");return}
  _,_=w.Write(b)
 })
 mux.HandleFunc("/api/v1/capabilities",func(w http.ResponseWriter,r *http.Request){
  if r.URL.RawQuery!=""{errorJSON(w,400,"invalid_query","capabilities have no query controls","");return}
  c,err:=capability.Build()
  if err!=nil{errorJSON(w,500,"catalog_invalid","internal source catalog invalid","");return}
  w.Header().Set("Content-Type","application/json; charset=utf-8")
  _=json.NewEncoder(w).Encode(c)
 })
 mux.HandleFunc("/api/v1/preview",func(w http.ResponseWriter,r *http.Request){
  if len(r.URL.RawQuery)>200{errorJSON(w,400,"invalid_query","query exceeds bound","");return}
  values:=r.URL.Query()
  if len(values)!=1&&len(values)!=2{errorJSON(w,400,"invalid_query","exactly action and optional scenario required","");return}
  for key:=range values{
   if key!="action"&&key!="scenario"{errorJSON(w,400,"invalid_query","unknown query field","");return}
  }
  actionText,err:=exactString(values,"action")
  if err!=nil{errorJSON(w,400,"invalid_action",err.Error(),"");return}
  c,err:=capability.Build()
  if err!=nil{errorJSON(w,500,"catalog_invalid","source catalog invalid","");return}
  entry,known:=capability.Find(c,behavior.Action(actionText))
  if !known{errorJSON(w,404,"unknown_action","action is not in the canonical contract",actionText);return}
  if entry.Mode!=capability.Preview{
   errorJSON(w,409,"contract_only_no_audio","typed state exists, but no synthetic audio was admitted",actionText)
   return
  }
  if len(values)!=2{errorJSON(w,400,"scenario_required","audio preview requires exact scenario name",actionText);return}
  scenario,err:=exactString(values,"scenario")
  if err!=nil{errorJSON(w,400,"invalid_scenario",err.Error(),actionText);return}
  if !validScenario(entry.AvailableSyntheticScenarios,scenario){
   errorJSON(w,422,"scenario_not_supported","scenario does not belong to the selected action",actionText);return
  }
  p,ok:=preview.Fixtures()[scenario]
  if !ok||p.Action!=entry.Action||p.Classification!=behavior.Classification{
   errorJSON(w,500,"fixture_mismatch","source evidence no longer matches advertised capability",actionText)
   return
  }
  wav,receipt,err:=preview.Render(p)
  if err!=nil{errorJSON(w,500,"render_invalid","original synthetic source could not render",actionText);return}
  byteSHA:=fmt.Sprintf("%x",sha256.Sum256(wav))
  if byteSHA!=receipt.SHA256{errorJSON(w,500,"integrity_failure","audio SHA mismatch",actionText);return}
  w.Header().Set("Content-Type","audio/wav")
  w.Header().Set("Content-Disposition","inline; filename=synthetic-performance.wav")
  w.Header().Set("X-Audio-SHA256",byteSHA)
  w.Header().Set("X-Preview-Action",actionText)
  w.Header().Set("X-Preview-Scenario",scenario)
  w.Header().Set("Content-Length",strconv.Itoa(len(wav)))
  _,_=w.Write(wav)
 })
 return http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){
  common(w)
  if r.Method!=http.MethodGet||r.ContentLength>0{
   if r.Method!=http.MethodGet{w.Header().Set("Allow","GET");errorJSON(w,405,"method_not_allowed","read-only synthetic research API","");return}
   errorJSON(w,400,"request_body_forbidden","no body, media upload or microphone accepted","");return
  }
  // Reject DNS-rebound Host headers and ambiguous absolute-form hosts, but
  // accept valid absolute-URI requests whose authority matches loopback Host.
  host,_,hostErr:=net.SplitHostPort(r.Host)
  if hostErr!=nil||(host!="127.0.0.1"&&host!="::1")||
   len(r.URL.Path)>128||strings.Contains(r.URL.Path,"..")||
   (r.URL.Host!=""&&r.URL.Host!=r.Host){
   errorJSON(w,400,"unsafe_request","non-loopback host or invalid local path","");return
  }
  // Same-origin browser controls only; a special Origin such as "null" is
  // not a bypass. Local non-browser clients may omit the Origin header.
  if origin:=r.Header.Get("Origin");origin!=""&&origin!="http://"+r.Host{
   errorJSON(w,403,"cross_origin_denied","preview is local and source-only","");return
  }
  mux.ServeHTTP(w,r)
 })
}
// API-level success is separate from browser/mobile/assistive HIL.
var ErrNotQualified=errors.New("not validated for physical voice, real anatomy, identity or medical safety")
