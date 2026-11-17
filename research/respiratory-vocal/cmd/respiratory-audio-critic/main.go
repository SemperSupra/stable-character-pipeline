// respiratory-audio-critic reports original source-independent PCM metrics
// against separately generated PUBLIC synthetic fixture WAV bytes only.
// It never treats a coherent spectral bin as an identified human voice F0.
package main
import(
 "encoding/json"
 "fmt"
 "os"
 "sort"

 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/observer"
 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/preview"
)
type Result struct{
 Name string `json:"name"`
 observer.Metrics
 EvidenceAt180Hz observer.ToneEvidence `json:"evidence_at_180_hz"`
 EvidenceAt900Hz observer.ToneEvidence `json:"evidence_at_900_hz"`
}
type Batch struct{
 Schema string `json:"schema"`
 Validity string `json:"validity"`
 Results []Result `json:"results"`
}
func main(){
 fixtures:=preview.Fixtures()
 names:=make([]string,0,len(fixtures))
 for name:=range fixtures{names=append(names,name)}
 sort.Strings(names)
 out:=Batch{Schema:"respiratory.source_blind_pcm_batch.v0",
  Validity:"synthetic_signal_diagnostics_not_human_pitch_or_anatomy",Results:[]Result{}}
 for _,name:=range names{
  wav,_,err:=preview.Render(fixtures[name]);if err!=nil{fail(err)}
  m,err:=observer.AnalyzeWAV(wav);if err!=nil{fail(err)}
  a,err:=observer.EvidenceAt(wav,180);if err!=nil{fail(err)}
  b,err:=observer.EvidenceAt(wav,900);if err!=nil{fail(err)}
  out.Results=append(out.Results,Result{Name:name,Metrics:m,EvidenceAt180Hz:a,EvidenceAt900Hz:b})
 }
 if len(out.Results)!=17{fail(fmt.Errorf("missing source fixture"))}
 enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ")
 if err:=enc.Encode(out);err!=nil{fail(err)}
}
func fail(err error){fmt.Fprintln(os.Stderr,"INVALID:",err);os.Exit(2)}
