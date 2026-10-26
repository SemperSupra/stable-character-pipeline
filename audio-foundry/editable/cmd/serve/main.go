// Command serve exposes the static source editor only on the local loopback.
// The editor reads project files through the user's browser File API; the server
// never receives, saves, transforms or uploads private project content.
package main

import (
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"time"
)

func main() {
	root := flag.String("root", "browser", "directory containing editor index.html")
	port := flag.Int("port", 8787, "local TCP port 1..65535")
	flag.Parse()
	if *port < 1 || *port > 65535 {
		log.Fatal("invalid local port")
	}
	st, e := os.Stat(*root)
	if e != nil || !st.IsDir() {
		log.Fatal("missing browser root")
	}
	listener, e := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", *port))
	if e != nil {
		log.Fatal(e)
	}
	log.Printf("Open http://127.0.0.1:%d in a local browser. No external interface bound.", *port)
	server := &http.Server{Handler: http.FileServer(http.Dir(*root)), ReadHeaderTimeout: 5 * time.Second, IdleTimeout: 30 * time.Second}
	log.Fatal(server.Serve(listener))
}