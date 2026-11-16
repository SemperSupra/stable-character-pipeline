// wavcheck measures existing source WAVs without any AI model or cloud service.
package main
import (
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "github.com/SemperSupra/stable-character-pipeline/research/audio-critic-cpu"
)
func main(){
 path:=flag.String("wav","","PCM16 mono WAV to inspect")
 flag.Parse()
 if *path=="" {fmt.Fprintln(os.Stderr,"-wav is required");os.Exit(2)}
 b,e:=os.ReadFile(*path);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
 m,e:=critic.Measure(b);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
 enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ");if e:=enc.Encode(m);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
 if m.Silent||m.ClippedSamples>0{os.Exit(3)}
}
