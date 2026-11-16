// gas-audition emits two public-safe illustrative vowel-like WAVs.
// Never interpret these as physiologically validated speech or breathable gas.
package main
import(
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "path/filepath"

 medium "github.com/SemperSupra/stable-character-pipeline/research/physical-medium"
 "github.com/SemperSupra/stable-character-pipeline/research/physical-medium/gasvoice"
)
type Result struct {
 Case string `json:"case"`
 gasvoice.Report
}
func main(){
 out:=flag.String("out","","nonexistent output directory for synthetic audio")
 flag.Parse()
 if *out==""{fmt.Fprintln(os.Stderr,"-out is required");os.Exit(2)}
 earth:=medium.Earthlike()
 other:=medium.Earthlike()
 other.Species[0].MoleFraction=0.74
 other.Species[2].MoleFraction=0.05
 results:=[]Result{}
 for i,c:=range []struct{name string;mix medium.State}{{"earthlike_proxy",earth},{"argon_shift_proxy_not_breathing_certified",other}}{
  prop,err:=c.mix.Evaluate();if err!=nil{fatal(err)}
  wav,report,err:=gasvoice.Generate(gasvoice.Params{SoundSpeed:prop.SoundSpeed,SourceF0:150,TractLength:0.17,SampleRate:48000,Samples:48000})
  if err!=nil{fatal(err)}
  if i==0{if err=os.Mkdir(*out,0700);err!=nil{fatal(err)}}
  path:=filepath.Join(*out,c.name+".wav")
  f,err:=os.OpenFile(path,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600);if err!=nil{fatal(err)}
  _,writeErr:=f.Write(wav);closeErr:=f.Close()
  if writeErr!=nil{fatal(writeErr)};if closeErr!=nil{fatal(closeErr)}
  results=append(results,Result{c.name,report})
 }
 if err:=json.NewEncoder(os.Stdout).Encode(results);err!=nil{fatal(err)}
}
func fatal(err error){
 if err==nil{err=errors.New("unknown error")}
 fmt.Fprintln(os.Stderr,err);os.Exit(2)
}
