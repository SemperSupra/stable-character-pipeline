package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	av "semper-supra.local/equine/av_observer"
)

func main() {
	events := flag.String("events", "", "source-original planned contact events JSON")
	audio := flag.String("audio", "", "native audio file or H264/AAC multiplex")
	receipt := flag.String("receipt", "", "independent JSON receipt destination")
	flag.Parse()
	if *events == "" || *audio == "" || *receipt == "" {
		fmt.Fprintln(os.Stderr, "-events -audio -receipt required")
		os.Exit(2)
	}
	b, err := os.ReadFile(*events)
	if err != nil {
		fatal(err)
	}
	c, err := av.ParseClock(b)
	if err != nil {
		fatal(err)
	}
	total := c.FramesPerCycle*c.Cycles/c.FPS + 1
	pcm, err := av.Decode(*audio, total)
	if err != nil {
		fatal(err)
	}
	r, err := av.Observe(c, pcm)
	if err != nil {
		fatal(err)
	}
	rb, err := json.MarshalIndent(r, "", "  ")
	if err != nil {
		fatal(err)
	}
	if err = os.WriteFile(*receipt, append(rb, '\n'), 0644); err != nil {
		fatal(err)
	}
	fmt.Println(r.Verdict)
	if len(r.Reasons) > 0 {
		for _, s := range r.Reasons {
			fmt.Fprintln(os.Stderr, s)
		}
		os.Exit(1)
	}
}
func fatal(err error) { fmt.Fprintln(os.Stderr, err); os.Exit(2) }
