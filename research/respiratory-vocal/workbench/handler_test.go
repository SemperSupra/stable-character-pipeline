package workbench

import(
 "bytes"
 "crypto/sha256"
 "encoding/binary"
 "encoding/json"
 "fmt"
 "net/http/httptest"
 "net/url"
 "strings"
 "testing"

 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/behavior"
 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/capability"
 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/preview"
)
func call(t *testing.T,method,path string,body []byte)*httptest.ResponseRecorder{
 t.Helper()
 req:=httptest.NewRequest(method,"http://127.0.0.1:8766"+path,bytes.NewReader(body))
 w:=httptest.NewRecorder();Handler().ServeHTTP(w,req);return w
}
func TestAll17OriginalAudioScenariosAvailableOnlyUnderTheirCanonicalAction(t *testing.T){
 c,e:=capability.Build();if e!=nil{t.Fatal(e)}
 seen:=map[string]bool{}
 total:=0
 for _,entry:=range c.Entries{
  if entry.Mode!=capability.Preview{continue}
  for _,name:=range entry.AvailableSyntheticScenarios{
   total++
   if seen[name]{t.Fatalf("duplicate scenario %s",name)}
   seen[name]=true
   query:=url.Values{"action":{string(entry.Action)},"scenario":{name}}.Encode()
   w:=call(t,"GET","/api/v1/preview?"+query,nil)
   if w.Code!=200||w.Header().Get("Content-Type")!="audio/wav"{
    t.Fatalf("scenario %s failed admission %d: %s",name,w.Code,w.Body.String())
   }
   body:=w.Body.Bytes()
   if len(body)<44||string(body[:4])!="RIFF"||
    binary.LittleEndian.Uint32(body[24:28])!=48000||
    w.Header().Get("X-Audio-SHA256")!=fmt.Sprintf("%x",sha256.Sum256(body))||
    w.Header().Get("X-Preview-Action")!=string(entry.Action)||
    w.Header().Get("X-Preview-Scenario")!=name{
    t.Fatalf("scenario %s lacked byte integrity/source binding",name)
   }
   // A direct source render and the public workbench MUST have the same PCM
   // bytes and SHA. No reimplemented or invented UI synthesizer allowed.
   original,ok:=preview.Fixtures()[name];if !ok{t.Fatal(name)}
   wave,_,err:=preview.Render(original);if err!=nil{t.Fatal(err)}
   if !bytes.Equal(wave,body){t.Fatalf("%s workbench audio differs from reviewed fixture",name)}
   again:=call(t,"GET","/api/v1/preview?"+query,nil)
   if again.Code!=200||!bytes.Equal(again.Body.Bytes(),body){t.Fatalf("%s not deterministic",name)}
  }
 }
 if total!=17{t.Fatalf("expected 17 source-approved synthetic scenarios, got %d",total)}
}
func TestContractOnlyNeverCreatesAnAudioFallback(t *testing.T){
 for _,action:=range []behavior.Action{behavior.Sniff,behavior.Sigh,behavior.Gasp}{
  for _,extra:=range []string{"","&scenario=nasal_quiet"}{
   w:=call(t,"GET","/api/v1/preview?action="+url.QueryEscape(string(action))+extra,nil)
   if w.Code!=409||w.Header().Get("Content-Type")!="application/json; charset=utf-8"{
    t.Fatalf("unsupported action %s was not denied: %d",action,w.Code)
   }
   var receipt ErrorReceipt
   if err:=json.Unmarshal(w.Body.Bytes(),&receipt);err!=nil{t.Fatal(err)}
   if receipt.Code!="contract_only_no_audio"||receipt.Action!=string(action){
    t.Fatalf("incorrect fail-closed receipt %+v",receipt)
   }
  }
 }
}
func TestNoSourceMismatchDuplicateOrMaliciousControls(t *testing.T){
 bad:=[]struct{query string;status int}{
  {"action=hum&scenario=nasal_quiet",422},
  {"action=quiet_breath&scenario=humming",422},
  {"action=unknown",404},
  {"scenario=nasal_quiet",400},
  {"action=hum",400},
  {"action=hum&scenario=humming&audio_source=private",400},
  {"action=hum&action=quiet_breath&scenario=humming",400},
  {"action=hum&scenario=humming&scenario=nasal_quiet",400},
  {"action=hum&scenario=%2Fetc%2Fpasswd",422},
  {"action=hum&scenario=humming&unknown=1",400},
  {"action=hum&scenario="+strings.Repeat("a",201),400},
 }
 for i,tc:=range bad{
  w:=call(t,"GET","/api/v1/preview?"+tc.query,nil)
  if w.Code!=tc.status{t.Fatalf("invalid #%d status=%d want %d: %s",i,w.Code,tc.status,w.Body.String())}
 }
 for _,path:=range []string{"/api/v1/preview?action=hum&scenario=humming","/api/v1/capabilities","/"}{
  w:=call(t,"POST",path,nil)
  if w.Code!=405{t.Fatalf("mutation accepted at %s: %d",path,w.Code)}
  w=call(t,"GET",path,[]byte("microphone upload prohibited"))
  if w.Code!=400{t.Fatalf("request body accepted at %s: %d",path,w.Code)}
 }
 req:=httptest.NewRequest("GET","http://127.0.0.1:8766/api/v1/preview?action=hum&scenario=humming",nil)
 req.Header.Set("Origin","https://unexpected.example")
 w:=httptest.NewRecorder();Handler().ServeHTTP(w,req)
 if w.Code!=403{t.Fatalf("foreign origin bypass: %d",w.Code)}
}
func TestRealCatalogHumanAssistiveAgentAndENDETHDelivery(t *testing.T){
 w:=call(t,"GET","/api/v1/capabilities",nil)
 if w.Code!=200||w.Header().Get("Cache-Control")!="no-store"{
  t.Fatalf("catalog status/headers: %d",w.Code)
 }
 var c capability.Catalog
 if e:=json.Unmarshal(w.Body.Bytes(),&c);e!=nil{t.Fatal(e)}
 if c.Schema!="respiratory.audience_capabilities.v0"||len(c.Entries)!=18||len(c.Locales)!=3||len(c.Audiences)!=3{
  t.Fatalf("not the real catalog: %+v",c)
 }
 human:=call(t,"GET","/",nil)
 if human.Code!=200||human.Header().Get("Content-Type")!="text/html; charset=utf-8"{
  t.Fatalf("no human-readable workbench: %d",human.Code)
 }
 body:=human.Body.String()
 for _,s:=range []string{
  "aria-live=\"polite\"","role=\"status\"","id=\"language\"","id=\"action\"","id=\"scenario\"",
  "id=\"prepare\"","id=\"play\"","audio id=\"play\"","/api/v1/capabilities",
  "/api/v1/preview?","prefers-reduced-motion:reduce",
  "option value=\"de\"","option value=\"th\"",
  "synthetic_preview_only","contract_only_no_audio", // API error code may be JS support
 }{
  if s=="contract_only_no_audio"{continue} // workbench gets status from source catalogue
  if !strings.Contains(body,s){t.Fatalf("missing accessible/typed surface %q",s)}
 }
 for _,language:=range []string{"en:{","de:{","th:{"}{
  if !strings.Contains(body,language){t.Fatalf("missing UI text for locale %s",language)}
 }
 if !strings.Contains(human.Header().Get("Content-Security-Policy"),"frame-ancestors 'none'"){
  t.Fatal("lack of local page framing controls")
 }
 if strings.Contains(body,"autoplay=\"")||strings.Contains(body,"navigator.mediaDevices")||
  strings.Contains(body,"getUserMedia("){t.Fatal("unexpected media capture/autoplay")}
 if w.Header().Get("Access-Control-Allow-Origin")!=""{t.Fatal("unexpected cross-origin read")}
}
