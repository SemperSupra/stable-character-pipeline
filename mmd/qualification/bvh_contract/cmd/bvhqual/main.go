// Original authored BVH CLI for human, automation and agent evaluation.
package main

import (
	"crypto/sha256"
	"encoding/json"
	"errors"
	"example.org/scp/bvhcontract"
	"flag"
	"fmt"
	"os"
	"path/filepath"
)

// Exact-source gate: only the two files originally authored and reviewed for
// this source-safe demonstration are admitted. A claim in a CLI flag or a
// filename cannot confer permission to process a third-party mocap capture.
var authoredFixtureSHAs = map[string]bool{
	"ab3a0d712c9c4f21fba0cf0698568dd5f88f1b959cf8aae28173c6435153d760": true,
	"1c6201e3b23bbbfdaef964b12baeb143835056150f83031da6dcdbcb992f450d": true,
}

func admittedFixture(data []byte) bool {
	d := sha256.Sum256(data)
	return authoredFixtureSHAs[fmt.Sprintf("%x", d[:])]
}

func run(args []string) error {
	f := flag.NewFlagSet("bvhqual", flag.ContinueOnError)
	source := f.String("source", "", "original authored self-test fixture")
	other := f.String("other", "", "optional distinct paired authored fixture")
	unit := f.Float64("meters-per-unit", 0, "explicit positive source scale")
	out := f.String("out", "", "new JSON receipt (refuse overwrite)")
	caps := f.Bool("capabilities", false, "read-only agent capabilities")
	if e := f.Parse(args); e != nil {
		return e
	}
	if *caps {
		fmt.Println(`{"schema":"scp.bvhqual.agent-capabilities.v1","actions":["capabilities","inspect_original_synthetic"],"private_R009":"HELD"}`)
		return nil
	}
	if f.NArg() > 0 || *source == "" || *out == "" || *unit <= 0 {
		return errors.New("source/out/explicit-positive-unit required")
	}
	if filepath.Clean(*source) == filepath.Clean(*out) {
		return errors.New("refuse overwrite source")
	}
	data, e := os.ReadFile(*source)
	if e != nil {
		return e
	}
	if !admittedFixture(data) {
		return errors.New("BVH_UNADMITTED_ORIGINAL_SOURCE_BYTES")
	}
	parsed, e := bvh.Parse(data, "ORIGINAL_SELF_AUTHORED_SYNTHETIC", *unit)
	if e != nil {
		return e
	}
	first, e := parsed.Evaluate(0)
	if e != nil {
		return e
	}
	last, e := parsed.Evaluate(len(parsed.Frames) - 1)
	if e != nil {
		return e
	}
	result := map[string]any{"schema": "scp.bvh.original-synthetic-inspection.v1", "status": "PASS_ORIGINAL_SYNTHETIC_BVH_FK_ONLY", "source_sha256": parsed.SourceSHA256, "frames": len(parsed.Frames), "frame_time_seconds": parsed.FrameTimeSeconds, "meters_per_unit": *unit, "joints": parsed.Joints, "first_frame": first, "last_frame": last, "original_mocap_file": "NOT_ADMITTED", "native_MMD_playback": "NOT_RUN", "private_R009": "HELD_NOT_ACCEPTED"}
	if *other != "" {
		if *other == *source {
			return errors.New("two actors cannot alias same file")
		}
		src, e := os.ReadFile(*other)
		if e != nil {
			return e
		}
		if !admittedFixture(src) {
			return errors.New("BVH_UNADMITTED_PAIRED_SOURCE_BYTES")
		}
		second, e := bvh.Parse(src, "ORIGINAL_SELF_AUTHORED_SYNTHETIC", *unit)
		if e != nil {
			return e
		}
		pair, e := bvh.CheckPair(parsed, second)
		if e != nil {
			return e
		}
		result["pair"] = pair
	}
	b, e := json.MarshalIndent(result, "", "  ")
	if e != nil {
		return e
	}
	fobj, e := os.OpenFile(*out, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if e != nil {
		return e
	}
	if _, e = fobj.Write(append(b, byte(10))); e != nil {
		fobj.Close()
		os.Remove(*out)
		return e
	}
	if e = fobj.Close(); e != nil {
		os.Remove(*out)
		return e
	}
	return nil
}
func main() {
	if e := run(os.Args[1:]); e != nil {
		fmt.Fprintln(os.Stderr, "BVH_QUALIFICATION_FAIL_CLOSED:", e)
		os.Exit(2)
	}
}
