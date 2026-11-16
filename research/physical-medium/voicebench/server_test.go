package voicebench

import (
 "bytes"
 "crypto/sha256"
 "encoding/binary"
 "encoding/json"
 "fmt"
 "net/http/httptest"
 "strings"
 "testing"
)
func request(t *testing.T,method,path string,body []byte)*httptest.ResponseRecorder{
 t.Helper()
 r:=httptest.NewRequest(method,path,bytes.NewReader(body))
 w:=httptest.NewRecorder()
 Handler().ServeHTTP(w,r)
 return w
}
func TestTypedHumanAutomationAgentContract(t *testing.T){
 w:=request(t,"GET","http://127.0.0.1/api/v1/controls",nil)
 if w.Code!=200{t.Fatalf("controls endpoint %d: %s",w.Code,w.Body)}
 var cap Capabilities
 if err:=json.Unmarshal(w.Body.Bytes(),&cap);err!=nil{t.Fatal(err)}
 if cap.Schema!="voicebench.control_capabilities.v0"||cap.Model!="research.continuous_resonator.v0"||
 len(cap.Audiences)!=3||len(cap.Controls)!=3||cap.DurationMS!=250||cap.SampleRate!=48000{
  t.Fatalf("inconsistent typed controls %+v",cap)
 }
 for _,c:=range cap.Controls{
  if c.Default<c.Min||c.Default>c.Max||c.Min>=c.Max||c.Unit==""{t.Fatalf("invalid control %+v",c)}
 }
 if len(cap.Unsupported)<6{t.Fatal("must disclose unavailable engine capabilities")}
 if w.Header().Get("Cache-Control")!="no-store"{t.Fatal("local audio inputs must not be cached")}
}
func TestSyntheticPreviewBackendReplayAndFineControl(t *testing.T){
 const prefix="http://127.0.0.1/api/v1/preview?"
 paths:=[]string{
  prefix+"length_mm=170&sound_speed=343.22218086816235&pitch_hz=160",
  prefix+"length_mm=171&sound_speed=343.22218086816235&pitch_hz=160",
  prefix+"length_mm=170&sound_speed=341.22131803948224&pitch_hz=160",
 }
 wavs:=[][]byte{}
 for _,url:=range paths {
  w:=request(t,"GET",url,nil)
  if w.Code!=200||w.Header().Get("Content-Type")!="audio/wav"{t.Fatalf("preview: %d %s",w.Code,w.Body)}
  b:=w.Body.Bytes()
  if len(b)!=44+12000*2||string(b[:4])!="RIFF"||string(b[8:12])!="WAVE"||
  binary.LittleEndian.Uint32(b[24:28])!=48000{
   t.Fatal("bad 48kHz synthetic WAV")
  }
  digest:=fmt.Sprintf("%x",sha256.Sum256(b))
  if w.Header().Get("X-Audio-SHA256")!=digest{t.Fatal("unbound WAV byte hash")}
  peak:=0
  for i:=44;i<len(b);i+=2{
   x:=int(int16(binary.LittleEndian.Uint16(b[i:i+2])))
   if x<0{x=-x};if x>peak{peak=x}
  }
  if peak==0||peak>=32760{t.Fatalf("silence or clipping peak=%d",peak)}
  wavs=append(wavs,append([]byte(nil),b...))
 }
 if bytes.Equal(wavs[0],wavs[1])||bytes.Equal(wavs[0],wavs[2]){
  t.Fatal("one-millimeter or altered gas control did not change audio bytes")
 }
 again:=request(t,"GET",paths[0],nil)
 if !bytes.Equal(wavs[0],again.Body.Bytes()){t.Fatal("same controls not deterministic")}
}
func TestRejectUnadmittedAndMalformedRequests(t *testing.T){
 const p="http://127.0.0.1/api/v1/preview?"
 bad:=[]string{
  p+"length_mm=170&pitch_hz=160",
  p+"length_mm=170&pitch_hz=160&sound_speed=343&unknown=1",
  p+"length_mm=170&length_mm=200&pitch_hz=160&sound_speed=343",
  p+"length_mm=NaN&pitch_hz=160&sound_speed=343",
  p+"length_mm=170&pitch_hz=160&sound_speed=Infinity",
  p+"length_mm=401&pitch_hz=160&sound_speed=343",
  p+"length_mm=170&pitch_hz=0&sound_speed=343",
  p+"length_mm=170&pitch_hz=160&sound_speed=0",
 }
 for i,url:=range bad {
  w:=request(t,"GET",url,nil)
  if w.Code!=400{t.Fatalf("bad case %d returned %d",i,w.Code)}
 }
 for _,url:=range []string{"http://127.0.0.1/","http://127.0.0.1/api/v1/controls","http://127.0.0.1/api/v1/preview?length_mm=170&sound_speed=343&pitch_hz=160"} {
  w:=request(t,"POST",url,nil)
  if w.Code!=405{t.Fatalf("mutation unexpectedly admitted at %s: %d",url,w.Code)}
 }
 w:=request(t,"GET","http://127.0.0.1/",[]byte("not allowed"))
 if w.Code!=400{t.Fatal("request body accepted")}
}
func TestAccessibleMultilingualPageBoundaries(t *testing.T){
 w:=request(t,"GET","http://127.0.0.1/",nil)
 if w.Code!=200||!strings.Contains(w.Header().Get("Content-Security-Policy"),"frame-ancestors 'none'"){t.Fatal("missing UI/CSP")}
 page:=w.Body.String()
 checks:=[]string{"<html lang=\"en\">","value=\"en\"","value=\"de\"","value=\"th\"",
  "aria-live=\"polite\"","role=\"status\"","<label for=\"length\"","<label for=\"pitch\"","<label for=\"speed\"",
  "audio id=\"reference\"","audio id=\"modified\"","prefers-reduced-motion:reduce","const words=",
  "microphone","autoplay"}
 for _,term:=range checks {
  if !strings.Contains(strings.ToLower(page),strings.ToLower(term)){t.Fatalf("missing multilingual/accessibility control: %s",term)}
 }
 for _,lang:=range []string{"en:","de:","th:"}{
  if !strings.Contains(page,lang){t.Fatalf("missing translation dictionary %s",lang)}
 }
}

func TestDefaultNoviceABEqualsUnchangedReference(t *testing.T){
 // This explicitly catches the first source-review discrepancy where a
 // 343.2m/s slider default was contrasted against a 343.222180868m/s
 // reference and thereby created a false audible change at rest.
 cap:=CurrentCapabilities()
 if len(cap.Controls)!=3||
  cap.Controls[0].Default!=170||cap.Controls[1].Default!=160||
  cap.Controls[2].Default!=343.222{
  t.Fatal("control defaults unexpectedly changed")
 }
 html:=request(t,"GET","http://127.0.0.1/",nil).Body.String()
 for _,fragment:=range []string{
  "id=\"length\" type=\"range\" min=\"80\" max=\"400\" step=\"1\" value=\"170\"",
  "id=\"pitch\" type=\"range\" min=\"70\" max=\"600\" step=\"1\" value=\"160\"",
  "id=\"speed\" type=\"range\" min=\"100\" max=\"2000\" step=\".001\" value=\"343.222\"",
  "sound_speed:343.222",
 }{
  if !strings.Contains(html,fragment){t.Fatalf("UI default/reference mismatch: %s",fragment)}
 }
 url:="http://127.0.0.1/api/v1/preview?length_mm=170&pitch_hz=160&sound_speed=343.222"
 a:=request(t,"GET",url,nil)
 b:=request(t,"GET",url,nil)
 if a.Code!=200||b.Code!=200||!bytes.Equal(a.Body.Bytes(),b.Body.Bytes()){
  t.Fatal("default UI A/B should be bit-identical until a control changes")
 }
}
