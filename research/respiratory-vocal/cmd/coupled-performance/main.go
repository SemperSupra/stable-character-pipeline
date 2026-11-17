// coupled-performance records original bounded synthetic source mechanics
// and audio SHA receipts without uploading or persisting WAV files.
package main
import(
 "encoding/json"
 "fmt"
 "os"
 "sort"

 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/coupling"
 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/physics"
 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/preview"
)
type Case struct{
 Name string `json:"name"`
 coupling.Receipt
}
type Report struct{
 Schema string `json:"schema"`
 Scope string `json:"scope"`
 Cases []Case `json:"cases"`
}
func main(){
 cfg:=coupling.Config{Mechanics:physics.Config{
  ReferenceVolumeM3:.003,InitialVolumeM3:.003,MinimumVolumeM3:.001,MaximumVolumeM3:.006,
  ComplianceM3PerPa:1e-5,NasalResistancePaSPerM3:2e7,
  OralResistancePaSPerM3:3e7,PortResistancePaSPerM3:4e7,
 },NormalizationLossJ:1}
 fixtures:=preview.Fixtures()
 names:=make([]string,0,len(fixtures))
 for n:=range fixtures{names=append(names,n)};sort.Strings(names)
 out:=Report{Schema:"respiratory.coupled_synthetic_batch.v0",
  Scope:"original_public_synthetic_mechanics_and_audio_not_biological",
  Cases:make([]Case,0,len(names))}
 for _,name:=range names{
  _,r,err:=coupling.Render(fixtures[name],cfg)
  if err!=nil{fmt.Fprintln(os.Stderr,"INVALID:",name,err);os.Exit(2)}
  out.Cases=append(out.Cases,Case{Name:name,Receipt:r})
 }
 if len(out.Cases)!=17{fmt.Fprintln(os.Stderr,"missing original source fixtures");os.Exit(2)}
 enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ")
 if err:=enc.Encode(out);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
}
