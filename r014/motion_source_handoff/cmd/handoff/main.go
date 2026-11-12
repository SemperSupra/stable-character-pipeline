package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"github.com/SemperSupra/stable-character-pipeline/r014/motion_source_handoff"
)

func main() {
	packet:=flag.String("packet","existing_sources.catalog.v1.json","Existing upstream source catalog metadata, not raw motion data")
	out:=flag.String("out","","Machine receipt output file in disposable runtime")
	flag.Parse()
	if *out=="" {fmt.Fprintln(os.Stderr,"out required");os.Exit(2)}
	p,raw,e:=handoff.ReadPacket(*packet)
	if e!=nil {fmt.Fprintln(os.Stderr,"READ_PACKET_HOLD",e);os.Exit(3)}
	r,e:=handoff.Evaluate(p,raw)
	if e!=nil {fmt.Fprintln(os.Stderr,"SOURCE_HANDOFF_HOLD",e);os.Exit(4)}
	data,e:=json.MarshalIndent(r,"","  ")
	if e!=nil {fmt.Fprintln(os.Stderr,e);os.Exit(5)}
	if e=os.MkdirAll(filepath.Dir(*out),0755);e!=nil {fmt.Fprintln(os.Stderr,e);os.Exit(6)}
	if e=os.WriteFile(*out,append(data,'\n'),0644);e!=nil {fmt.Fprintln(os.Stderr,e);os.Exit(7)}
	fmt.Printf("R014_EXISTING_SOURCE_SEAM %s sources=%d R014=%s\n",r.Status,len(r.SourceDispositions),r.R014ReleaseStatus)
}
