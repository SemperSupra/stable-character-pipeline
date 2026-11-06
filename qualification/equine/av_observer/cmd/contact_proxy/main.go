package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	av "semper-supra.local/equine/av_observer"
)

func main() {
	planned := flag.String("planned", "", "pinned synthetic planned-event JSON")
	observed := flag.String("observed", "", "independently native-evaluated hoof science JSON")
	glb := flag.String("glb", "", "exact original synthetic GLB whose hoof geometry was observed")
	glbSHA := flag.String("glb-sha256", "", "independent pinned source GLB SHA256")
	output := flag.String("receipt", "", "destination JSON receipt")
	flag.Parse()
	if *planned == "" || *observed == "" || *glb == "" || *glbSHA == "" || *output == "" {
		fmt.Fprintln(os.Stderr, "-planned -observed -glb -glb-sha256 -receipt all required")
		os.Exit(2)
	}
	planBytes, err := os.ReadFile(*planned)
	if err != nil {
		die(err)
	}
	c, err := av.ParseClock(planBytes)
	if err != nil {
		die(err)
	}
	hoofBytes, err := os.ReadFile(*observed)
	if err != nil {
		die(err)
	}
	modelInfo, err := os.Stat(*glb)
	if err != nil {
		die(err)
	}
	if modelInfo.Size() > 64*1024*1024 {
		die(fmt.Errorf("model exceeds 64MiB"))
	}
	modelBytes, err := os.ReadFile(*glb)
	if err != nil {
		die(err)
	}
	// Preserve true evidence linkage instead of manufacturing another self-claimed ID.
	r, err := av.CheckContactProxy(c, hoofBytes, modelBytes, filepath.Base(*glb), *glbSHA)
	if err != nil {
		die(err)
	}
	out, err := json.MarshalIndent(r, "", "  ")
	if err != nil {
		die(err)
	}
	if err = os.WriteFile(*output, append(out, '\n'), 0644); err != nil {
		die(err)
	}
	fmt.Println(r.Verdict)
	if len(r.Reasons) > 0 {
		os.Exit(1)
	}
}
func die(err error) { fmt.Fprintln(os.Stderr, err); os.Exit(2) }
