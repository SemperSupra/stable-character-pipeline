package main
import (
 "flag"
 "log"
 "net/http"
 "time"
 "example.org/scp/anatomy-bakeoff/service"
)
func main(){
 addr:=flag.String("listen","127.0.0.1:8777","loopback HTTP host:port; no public exposure")
 flag.Parse()
 srv:=&http.Server{Addr:*addr,Handler:service.New(),ReadHeaderTimeout:5*time.Second,ReadTimeout:10*time.Second,WriteTimeout:10*time.Second}
 log.Printf("R036 synthetic anatomy viewer listening on %s",srv.Addr)
 log.Fatal(srv.ListenAndServe())
}
