package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
)

func main() {
	out := flag.String("out", "", "Output directory")
	flag.Parse()
	if *out == "" {
		panic("--out required")
	}
	if e := os.MkdirAll(*out, 0755); e != nil {
		panic(e)
	}
	frames, receipt := Simulate()
	b, e := json.MarshalIndent(frames, "", "  ")
	if e != nil {
		panic(e)
	}
	if e = os.WriteFile(filepath.Join(*out, "gait_frames.json"), append(b, '\n'), 0644); e != nil {
		panic(e)
	}
	b, e = json.MarshalIndent(receipt, "", "  ")
	if e != nil {
		panic(e)
	}
	if e = os.WriteFile(filepath.Join(*out, "gait_receipt.json"), append(b, '\n'), 0644); e != nil {
		panic(e)
	}
	fmt.Printf("R014_GAIT_MATH %s\n", string(b))
	if err := Render(frames, filepath.Join(*out, "frames")); err != nil {
		panic(err)
	}
	if receipt.Status != "PASS_TRAJECTORY_AND_CONTACT_PROOF_ONLY" {
		os.Exit(1)
	}
}
