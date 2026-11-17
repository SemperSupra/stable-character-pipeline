// respiratory-workbench is an original synthetic-only local demo.
// No human voice, real instrument physiology or protected media admitted.
package main
import(
 "flag"
 "fmt"
 "log"
 "net"
 "net/http"
 "time"

 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/workbench"
)
func main(){
 listen:=flag.String("listen","127.0.0.1:8766","local loopback address")
 flag.Parse()
 host,_,err:=net.SplitHostPort(*listen)
 if err!=nil||(host!="127.0.0.1"&&host!="::1"){
  log.Fatal("non-loopback listen denied: this synthetic prototype has no internet authentication")
 }
 server:=&http.Server{
  Addr:*listen,Handler:workbench.Handler(),
  ReadHeaderTimeout:4*time.Second,
  ReadTimeout:10*time.Second,
  WriteTimeout:10*time.Second,
  IdleTimeout:20*time.Second,
  MaxHeaderBytes:8192,
 }
 fmt.Printf("Synthetic-only respiratory workbench: http://%s\n",*listen)
 log.Fatal(server.ListenAndServe())
}
