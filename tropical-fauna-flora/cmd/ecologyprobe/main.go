// ecologyprobe exports the deterministic behavioral fixture as JSON for scene composition.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"github.com/SemperSupra/stable-character-pipeline/tropical-fauna-flora/ecology"
	"os"
	"path/filepath"
)

func main() {
	scenario := flag.String("config", "examples/earth.json", "scenario JSON")
	output := flag.String("out", "out/earth_ecology.json", "result JSON")
	flag.Parse()
	data, err := os.ReadFile(*scenario)
	fail(err)
	var s ecology.Scenario
	fail(json.Unmarshal(data, &s))
	r, err := ecology.Simulate(s)
	fail(err)
	fail(ecology.TraceIntegrity(r))
	rendered, err := json.MarshalIndent(r, "", "  ")
	fail(err)
	fail(os.MkdirAll(filepath.Dir(*output), 0755))
	fail(os.WriteFile(*output, append(rendered, '\n'), 0644))
	fmt.Printf("%s: ticks=%d digest=%s initial=%dg growth=%dg grazed=%dg final=%dg balanced=%t\n", s.Name, s.Ticks, r.DigestSHA256, r.Ledger.InitialG, r.Ledger.RegrowthG, r.Ledger.ConsumedG, r.Ledger.FinalG, r.Ledger.Balanced)
}
func fail(err error) {
	if err != nil {
		fmt.Fprintln(os.Stderr, "ecologyprobe:", err)
		os.Exit(1)
	}
}
