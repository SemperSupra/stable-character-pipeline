// performance-preview emits original, fixed synthetic sound examples only.
// No human voices, clinical safety claims, copyrighted clips or model weights.
package main

import(
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "path/filepath"
 "sort"

 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/preview"
)
type Row struct {
 Name string `json:"name"`
 preview.Receipt
}
type Run struct {
 Schema string `json:"schema"`
 Scope string `json:"scope"`
 Cases []Row `json:"cases"`
}
func main(){
 out:=flag.String("out","","new output directory for synthetic WAV examples")
 flag.Parse()
 if *out==""{fatal(errors.New("-out required"))}
 if e:=os.Mkdir(*out,0700);e!=nil{fatal(fmt.Errorf("output directory must be new: %w",e))}
 fixtures:=preview.Fixtures()
 names:=make([]string,0,len(fixtures))
 for k:=range fixtures{names=append(names,k)}
 sort.Strings(names)
 results:=Run{Schema:"respiratory.preview_batch.v0",
  Scope:"public_original_synthetic_only_not_anatomical_physiology_or_speaker",
  Cases:[]Row{}}
 for _,name:=range names{
  wav,receipt,e:=preview.Render(fixtures[name])
  if e!=nil{fatal(fmt.Errorf("%s invalid: %w",name,e))}
  f,e:=os.OpenFile(filepath.Join(*out,name+".wav"),os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
  if e!=nil{fatal(e)}
  n,writeErr:=f.Write(wav);closeErr:=f.Close()
  if writeErr!=nil{fatal(writeErr)};if closeErr!=nil{fatal(closeErr)}
  if n!=len(wav){fatal(errors.New("short WAV write"))}
  results.Cases=append(results.Cases,Row{Name:name,Receipt:receipt})
 }
 enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ")
 if e:=enc.Encode(results);e!=nil{fatal(e)}
}
func fatal(err error){fmt.Fprintln(os.Stderr,"INVALID:",err);os.Exit(2)}
