// voicebench is a synthetic-only loopback learning interface, NOT a public
// deployment or a calibrated human vocal-tract or speech service.
package main
import(
 "flag"
 "fmt"
 "log"
 "net"
 "net/http"
 "time"

 "github.com/SemperSupra/stable-character-pipeline/research/physical-medium/voicebench"
)
func main(){
 listen:=flag.String("listen","127.0.0.1:8765","localhost-only preview address")
 flag.Parse()
 host,_,err:=net.SplitHostPort(*listen)
 if err!=nil || host!="127.0.0.1"&&host!="::1"{
  log.Fatal("refuse non-loopback listening; this research-only service is not authenticated")
 }
 server:=&http.Server{
  Addr:*listen,
  Handler:voicebench.Handler(),
  ReadHeaderTimeout:5*time.Second,
  ReadTimeout:10*time.Second,
  WriteTimeout:10*time.Second,
  IdleTimeout:15*time.Second,
  MaxHeaderBytes:8192,
 }
 fmt.Printf("Synthetic-only local Voice Workbench at http://%s — no mic, no deployment\n",*listen)
 log.Fatal(server.ListenAndServe())
}
