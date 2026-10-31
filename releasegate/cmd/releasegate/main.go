package main
import ("encoding/json";"fmt";"os";"github.com/sempersupra/stable-character-pipeline/releasegate")
func main(){
 if len(os.Args)!=2{fmt.Fprintln(os.Stderr,"usage: releasegate manifest.json");os.Exit(2)}
 f,err:=os.Open(os.Args[1]);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 defer f.Close()
 d,err:=releasegate.Check(f)
 if err!=nil {fmt.Fprintln(os.Stderr,err)}
 _=json.NewEncoder(os.Stdout).Encode(d)
 if err!=nil||d.Status!="PASS"{os.Exit(1)}
}
