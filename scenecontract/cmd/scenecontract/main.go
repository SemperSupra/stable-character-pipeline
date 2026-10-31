package main
import(
 "encoding/json"
 "fmt"
 "log"
 "net/http"
 "os"
 "github.com/sempersupra/stable-character-pipeline/scenecontract"
)
func main(){
 if len(os.Args)<2{fmt.Fprintln(os.Stderr,"usage: scenecontract validate <scene.json> | serve");os.Exit(2)}
 switch os.Args[1]{
 case "validate":
  if len(os.Args)!=3{os.Exit(2)}
  f,err:=os.Open(os.Args[2]);if err!=nil{log.Print(err);os.Exit(2)}
  defer f.Close()
  d,err:=scenecontract.Evaluate(f)
  if err!=nil {log.Print(err)}
  _=json.NewEncoder(os.Stdout).Encode(d)
  if err!=nil||d.Status!="PASS"{os.Exit(1)}
 case "serve":
  if len(os.Args)!=2{os.Exit(2)}
  log.Print("reference conformance listener: http://127.0.0.1:8765")
  log.Fatal(http.ListenAndServe("127.0.0.1:8765",scenecontract.Handler()))
 default:os.Exit(2)
 }
}
