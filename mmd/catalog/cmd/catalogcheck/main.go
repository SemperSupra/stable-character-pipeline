package main
import ("encoding/json";"fmt";"os";"github.com/SemperSupra/stable-character-pipeline/mmd/catalog")
func main(){
 if len(os.Args)!=2{fmt.Fprintln(os.Stderr,"usage: catalogcheck catalog.json");os.Exit(2)}
 b,err:=os.ReadFile(os.Args[1]);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 c,err:=catalog.Validate(b);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 json.NewEncoder(os.Stdout).Encode(map[string]any{"schema":c.Schema,"entries":len(c.Entries),"status":"PASS_CATALOG_RIGHTS_ADMISSION"})
}
