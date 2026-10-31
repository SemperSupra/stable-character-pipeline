package main
import(
 "encoding/json"
 "fmt"
 "os"
 "github.com/sempersupra/stable-character-pipeline/releasegate"
 "github.com/sempersupra/stable-character-pipeline/releaseproof"
)
func main(){
 if len(os.Args)!=6||os.Args[1]!="verify"{fmt.Fprintln(os.Stderr,"usage: releaseproof verify manifest.json trust.json proofs-dir evidence-dir");os.Exit(2)}
 f,err:=os.Open(os.Args[2]);if err!=nil{fmt.Fprintln(os.Stderr,"manifest unavailable");os.Exit(2)}
 defer f.Close()
 m,err:=releasegate.Parse(f);if err!=nil{fmt.Fprintln(os.Stderr,"manifest invalid");os.Exit(2)}
 var policy releaseproof.TrustPolicy
 if err:=releaseproof.DecodeFile(os.Args[3],&policy);err!=nil{fmt.Fprintln(os.Stderr,"trust policy invalid");os.Exit(2)}
 result:=releaseproof.Verify(m,policy,os.Args[4],os.Args[5])
 _=json.NewEncoder(os.Stdout).Encode(result)
 if result.Status!="PASS"{os.Exit(1)}
}
