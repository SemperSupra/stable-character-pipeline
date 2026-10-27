// envelopecheck provides a read-only, stdin/file based capability usable by
// humans, CI automation and agent executors without a second state store.
package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"

	"github.com/SemperSupra/stable-character-pipeline/mmd/roadmap/envelope"
)

func main() {
	if len(os.Args)!=2 { fmt.Fprintln(os.Stderr,"usage: envelopecheck <proof-bundle.json|- for stdin>"); os.Exit(4) }
	var r io.Reader=os.Stdin
	if os.Args[1]!="-" {
		f,err:=os.Open(os.Args[1]); if err!=nil { fmt.Fprintln(os.Stderr,err); os.Exit(4) }
		defer f.Close()
		r=f
	}
	const maxSize=1<<20
	b,err:=io.ReadAll(io.LimitReader(r,maxSize+1))
	if err!=nil || len(b)>maxSize { fmt.Fprintln(os.Stderr,"proof input read error or >1 MiB"); os.Exit(4) }
	p,err:=envelope.DecodeStrict(b)
	if err!=nil { 
		_ = json.NewEncoder(os.Stdout).Encode(map[string]any{"validation":"INVALID","reason":err.Error()})
		os.Exit(4)
	}
	_ = json.NewEncoder(os.Stdout).Encode(map[string]any{"validation":"VALID_ENVELOPE_ONLY","source_rights":p.Fixture.Semantics.Rights.AssetRights,"verdict":p.Verdict,"observations":len(p.Observations),"metrics":len(p.Metrics),"source_sha256":p.Fixture.SourceSHA256})
}
