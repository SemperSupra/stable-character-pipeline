package main

import(
 "context"
 "encoding/json"
 "flag"
 "fmt"
 "log"
 "net"
 "net/http"
 "os"
 "time"
 "github.com/sempersupra/stable-character-pipeline/scenejob"
)
func fail(){fmt.Fprintln(os.Stderr,"usage: scenejob run|serve --revision GIT40 --output RESULTS_DIR --repo TRUSTED_SOURCE_ROOT");os.Exit(2)}
func main(){
 if len(os.Args)<2{fail()}
 mode:=os.Args[1]
 if mode!="run"&&mode!="serve"{fail()}
 flags:=flag.NewFlagSet(mode,flag.ContinueOnError)
 revision:=flags.String("revision","","exact public synthetic source HEAD SHA")
 output:=flags.String("output","","output root")
 repo:=flags.String("repo","","trusted source root")
 if err:=flags.Parse(os.Args[2:]);err!=nil||*output==""||*revision==""||*repo==""||flags.NArg()!=0{fail()}
 manager,err:=scenejob.NewManager(*revision,*output,scenejob.DockerEngine{RepoRoot:*repo,Image:"scp-native-oci:r9"})
 if err!=nil{log.Print("native manager rejected configuration: ",err);os.Exit(2)}
 if mode=="run"{
  r,err:=manager.Run(context.Background(),scenejob.Expected(*revision))
  if err!=nil{log.Print("native job did not qualify: ",err);os.Exit(1)}
  _=json.NewEncoder(os.Stdout).Encode(r)
  // Exit 0 means *technical native execution only*. Scientific FAIL and release HOLD are mandatory.
  return
 }
 listener,err:=net.Listen("tcp","127.0.0.1:8766")
 if err!=nil{log.Print(err);os.Exit(2)}
 server:=&http.Server{Handler:manager.Handler(),ReadHeaderTimeout:5*time.Second,
  ReadTimeout:10*time.Second,WriteTimeout:6*time.Minute,IdleTimeout:20*time.Second,
  MaxHeaderBytes:16384}
 log.Print("SOURCE_SAFE_LOOPBACK_NATIVE_JOB_RESEARCH_ONLY on 127.0.0.1:8766")
 if err:=server.Serve(listener);err!=nil&&err!=http.ErrServerClosed{log.Fatal(err)}
}
