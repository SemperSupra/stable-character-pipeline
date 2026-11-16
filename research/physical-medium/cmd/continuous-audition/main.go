// continuous-audition creates three original public-safe PCM WAV teaching
// examples. They are NOT recordings, real tract models or breathability tests.
package main
import(
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "path/filepath"

 "github.com/SemperSupra/stable-character-pipeline/research/physical-medium/continuous"
)
type Row struct {
 Case string `json:"case"`
 continuous.Receipt
}
func main(){
 out:=flag.String("out","","new target directory")
 flag.Parse()
 if *out==""{fatal(errors.New("-out required"))}
 if err:=os.Mkdir(*out,0700);err!=nil{fatal(fmt.Errorf("output must be new: %w",err))}
 cases:=[]struct{name string;length,c float64}{
  {"reference_170mm_earthlike",0.170,343.22218086816235},
  {"length_171mm_earthlike",0.171,343.22218086816235},
  {"reference_170mm_altered_gas",0.170,341.22131803948224},
 }
 rows:=[]Row{}
 for _,c:=range cases{
  wav,r,e:=continuous.Generate(continuous.Params{LengthM:c.length,SoundSpeedMPS:c.c,SourceHz:160,Samples:24000})
  if e!=nil{fatal(e)}
  f,e:=os.OpenFile(filepath.Join(*out,c.name+".wav"),os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
  if e!=nil{fatal(e)}
  n,we:=f.Write(wav);ce:=f.Close()
  if we!=nil{fatal(we)};if ce!=nil{fatal(ce)};if n!=len(wav){fatal(errors.New("short write"))}
  rows=append(rows,Row{c.name,r})
 }
 e:=json.NewEncoder(os.Stdout);e.SetIndent("","  ");if err:=e.Encode(rows);err!=nil{fatal(err)}
}
func fatal(e error){fmt.Fprintln(os.Stderr,"INVALID:",e);os.Exit(2)}
