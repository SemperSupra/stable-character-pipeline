// wavcheck measures existing source WAVs without any AI model or cloud service.
package main
import (
 "encoding/json"
 "flag"
 "fmt"
 "io"
 "os"
 "github.com/SemperSupra/stable-character-pipeline/research/audio-critic-cpu"
)
func main(){
 path:=flag.String("wav","","PCM16 mono WAV to inspect")
 flag.Parse()
 if *path=="" {fmt.Fprintln(os.Stderr,"-wav is required");os.Exit(2)}
 b,e:=readBounded(*path,critic.MaxBytes);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
 m,e:=critic.Measure(b);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
 enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ");if e:=enc.Encode(m);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
 if m.Silent||m.ClippedSamples>0{os.Exit(3)}
}

// readBounded enforces a byte cap before allocation, even for non-seekable inputs.
func readBounded(path string, limit int64) ([]byte,error) {
 if limit<=0{return nil,fmt.Errorf("invalid byte limit")}
 f,e:=os.Open(path);if e!=nil{return nil,e};defer f.Close()
 b,e:=io.ReadAll(io.LimitReader(f,limit+1));if e!=nil{return nil,e}
 if int64(len(b))>limit{return nil,fmt.Errorf("input exceeds %d byte limit",limit)}
 return b,nil
}
