// Package voicebench exposes an original, bounded, synthetic-only audio
// workbench. It is NOT private Physical Vocal, a human tract model or a
// deployed, authenticated public service. Local loopback demonstration only.
package voicebench

import (
 "crypto/sha256"
 "embed"
 "encoding/json"
 "fmt"
 "math"
 "net/http"
 "strconv"
 "strings"

 "github.com/SemperSupra/stable-character-pipeline/research/physical-medium/continuous"
)

//go:embed index.html
var assets embed.FS

type Control struct {
 ID string `json:"id"`
 Unit string `json:"unit"`
 Min float64 `json:"min"`
 Max float64 `json:"max"`
 Default float64 `json:"default"`
 Novice bool `json:"novice"`
 Description string `json:"description"`
}
type Capabilities struct {
 Schema string `json:"schema"`
 Model string `json:"model"`
 Validity string `json:"validity"`
 Audiences []string `json:"audiences"`
 Controls []Control `json:"controls"`
 DurationMS int `json:"duration_ms"`
 SampleRate int `json:"sample_rate_hz"`
 Unsupported []string `json:"unsupported"`
}
func CurrentCapabilities()Capabilities{
 return Capabilities{
  Schema:"voicebench.control_capabilities.v0",
  Model:"research.continuous_resonator.v0",
  Validity:"original_synthetic_source_filter_proxy_not_biological_or_identity",
  Audiences:[]string{"human_including_assistive_technology","automation","agent"},
  Controls:[]Control{
   {ID:"length_mm",Unit:"mm",Min:80,Max:400,Default:170,Novice:true,Description:"toy acoustic resonator length; not an anatomical measurement"},
   {ID:"pitch_hz",Unit:"Hz",Min:70,Max:600,Default:160,Novice:true,Description:"prescribed sinusoidal source frequency, not automatically validated perceived pitch"},
   {ID:"sound_speed",Unit:"m/s",Min:100,Max:2000,Default:343.22218086816235,Novice:false,Description:"interior acoustic medium proxy; not a breathing-safety or gas-composition model"},
  },
  DurationMS:250,SampleRate:continuous.Rate,
  Unsupported:[]string{"real_tract_anatomy","real_speech","real_voice_identity","continuous_mid_stream_geometry_switch","live_full_body_deformation","gas_breathability","true_environment_propagation","microphone_or_private_reference_input"},
 }
}
func setHeaders(w http.ResponseWriter){
 w.Header().Set("X-Content-Type-Options","nosniff")
 w.Header().Set("Referrer-Policy","no-referrer")
 w.Header().Set("Cache-Control","no-store")
 w.Header().Set("X-Model-Validity","synthetic-proxy-only")
}
func reject(w http.ResponseWriter,code int,message string){
 w.Header().Set("Content-Type","application/json; charset=utf-8")
 w.WriteHeader(code)
 _=json.NewEncoder(w).Encode(map[string]string{"error":message})
}
func value(query map[string][]string,key string,min,max float64)(float64,error){
 all,ok:=query[key]
 if !ok||len(all)!=1{return 0,fmt.Errorf("exactly one %s is required",key)}
 f,err:=strconv.ParseFloat(all[0],64)
 if err!=nil||math.IsNaN(f)||math.IsInf(f,0)||f<min||f>max{
  return 0,fmt.Errorf("%s outside bounded research range",key)
 }
 return f,nil
}
func Handler()http.Handler{
 mux:=http.NewServeMux()
 mux.HandleFunc("/",func(w http.ResponseWriter,r *http.Request){
  setHeaders(w)
  if r.URL.Path!="/"{http.NotFound(w,r);return}
  if r.Method!=http.MethodGet{reject(w,405,"only GET allowed");return}
  w.Header().Set("Content-Type","text/html; charset=utf-8")
  w.Header().Set("Content-Security-Policy","default-src 'none'; media-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
  b,err:=assets.ReadFile("index.html")
  if err!=nil{reject(w,500,"preview asset unavailable");return}
  _,_ = w.Write(b)
 })
 mux.HandleFunc("/api/v1/controls",func(w http.ResponseWriter,r *http.Request){
  setHeaders(w)
  if r.Method!=http.MethodGet{reject(w,405,"only GET allowed");return}
  w.Header().Set("Content-Type","application/json; charset=utf-8")
  _=json.NewEncoder(w).Encode(CurrentCapabilities())
 })
 mux.HandleFunc("/api/v1/preview",func(w http.ResponseWriter,r *http.Request){
  setHeaders(w)
  if r.Method!=http.MethodGet{reject(w,405,"only GET allowed");return}
  if len(r.URL.RawQuery)>256{reject(w,400,"overlong query");return}
  values:=r.URL.Query()
  if len(values)!=3{reject(w,400,"require exactly three known controls");return}
  for key:=range values{
   if key!="length_mm"&&key!="pitch_hz"&&key!="sound_speed"{reject(w,400,"unknown control");return}
  }
  l,err:=value(values,"length_mm",80,400);if err!=nil{reject(w,400,err.Error());return}
  pitch,err:=value(values,"pitch_hz",70,600);if err!=nil{reject(w,400,err.Error());return}
  speed,err:=value(values,"sound_speed",100,2000);if err!=nil{reject(w,400,err.Error());return}
  wav,receipt,err:=continuous.Generate(continuous.Params{LengthM:l/1000,SoundSpeedMPS:speed,SourceHz:pitch,Samples:12000})
  if err!=nil{reject(w,400,"unsupported synthetic research configuration");return}
  expected:=fmt.Sprintf("%x",sha256.Sum256(wav))
  if receipt.WAVSHA256!=expected{reject(w,500,"internal signal integrity failure");return}
  w.Header().Set("Content-Type","audio/wav")
  w.Header().Set("X-Audio-SHA256",expected)
  w.Header().Set("Content-Disposition","inline; filename=synthetic-preview.wav")
  w.Header().Set("Content-Length",strconv.Itoa(len(wav)))
  _,_=w.Write(wav)
 })
 return http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){
  // Prevent exotic methods or large request bodies from being accepted by
  // the local preview. No POST/microphone/session-upload capability exists.
  if r.ContentLength>0||strings.Contains(r.URL.Path,".."){
   setHeaders(w);reject(w,400,"only bodyless local requests");return
  }
  mux.ServeHTTP(w,r)
 })
}
