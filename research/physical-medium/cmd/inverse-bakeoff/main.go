// inverse-bakeoff reports a bounded, frozen, synthetic-only search experiment.
// It cannot infer or verify a real human vocal tract from recordings.
package main
import(
 "encoding/json"
 "fmt"
 "os"
 "github.com/SemperSupra/stable-character-pipeline/research/physical-medium"
 "github.com/SemperSupra/stable-character-pipeline/research/physical-medium/gasvoice"
 "github.com/SemperSupra/stable-character-pipeline/research/physical-medium/inverse"
)
type Row struct{
 inverse.Result
 HeldOutMSE float64 `json:"held_out_pcm_mse"`
}
func main(){
 p,e:=medium.Earthlike().Evaluate();if e!=nil{fatal(e)}
 c:=inverse.Config{KnownSoundSpeed:p.SoundSpeed,SourceF0:160,MinLength:0.13,MaxLength:0.23,SampleRate:48000,Samples:4800,Budget:12}
 targetLength:=0.178
 target,_,e:=gasvoice.Generate(gasvoice.Params{SoundSpeed:p.SoundSpeed,SourceF0:160,TractLength:targetLength,SampleRate:c.SampleRate,Samples:c.Samples});if e!=nil{fatal(e)}
 heldTrue,_,e:=gasvoice.Generate(gasvoice.Params{SoundSpeed:p.SoundSpeed,SourceF0:190,TractLength:targetLength,SampleRate:c.SampleRate,Samples:c.Samples});if e!=nil{fatal(e)}
 rows:=[]Row{}
 for _,seed:=range []int64{11,23,37,71}{
  c.Seed=seed
  for _,method:=range []string{"random","golden"}{
   r,e:=inverse.Fit(target,c,method);if e!=nil{fatal(e)}
   heldGuess,_,e:=gasvoice.Generate(gasvoice.Params{SoundSpeed:p.SoundSpeed,SourceF0:190,TractLength:r.BestLength,SampleRate:c.SampleRate,Samples:c.Samples});if e!=nil{fatal(e)}
   hold,e:=inverse.Loss(heldTrue,heldGuess);if e!=nil{fatal(e)}
   rows=append(rows,Row{r,hold})
  }
 }
 enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ");if e:=enc.Encode(rows);e!=nil{fatal(e)}
}
func fatal(e error){fmt.Fprintln(os.Stderr,e);os.Exit(2)}
