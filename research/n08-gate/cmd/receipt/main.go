package main
import (
 "encoding/json"
 "fmt"
 "os"
 "runtime"
 "github.com/SemperSupra/stable-character-pipeline/research/n08-gate/gate"
)
func main(){
 s:=gate.NewStore()
 source:=[]byte("original-synthetic-state")
 state:=s.Snapshot()
 result:=struct{
 Schema string `json:"schema"`
 GoVersion string `json:"go_version"`
 GOOS string `json:"goos"`
 Status string `json:"status"`
 Initial gate.State `json:"initial"`
 OwnerAccepted bool `json:"owner_accepted"`
 ReleaseAuthorized bool `json:"release_authorized"`
 }{"scp.n08.synthetic-cas-receipt.v1",runtime.Version(),runtime.GOOS,"PASS_NARROW",state,false,false}
 if len(source)==0{os.Exit(12)}
 b,e:=json.MarshalIndent(result,"","  ")
 if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(12)}
 fmt.Println(string(b))
}
