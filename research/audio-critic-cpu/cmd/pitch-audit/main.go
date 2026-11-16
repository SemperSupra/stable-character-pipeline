// pitch-audit produces source-independent diagnostic octave evidence, not
// an approved or calibrated speech/speaker F0 label.
package main
import(
 "encoding/json"
 "flag"
 "fmt"
 "io"
 "os"
 "github.com/SemperSupra/stable-character-pipeline/research/audio-critic-cpu"
)
func main(){
 path:=flag.String("wav","","bounded synthetic WAV file")
 flag.Parse()
 if *path==""{fmt.Fprintln(os.Stderr,"-wav required");os.Exit(2)}
 f,e:=os.Open(*path);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
 defer f.Close()
 b,e:=io.ReadAll(io.LimitReader(f,int64(critic.MaxBytes)+1))
 if e!=nil||len(b)>critic.MaxBytes{fmt.Fprintln(os.Stderr,"invalid or oversized source");os.Exit(2)}
 audit,e:=critic.AuditPitchWAV(b)
 if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
 enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ")
 if e:=enc.Encode(audit);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
 // Abstention is normal: emit usable machine-readable receipt and do not
 // treat unresolved perceptual evidence as a failed integrity check.
}
