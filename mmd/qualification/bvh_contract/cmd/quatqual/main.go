// Native portable source quaternion receipt for originally authored BVH only.
// No arbitrary source admission, private runner or real mocap.
package main

import (
	"crypto/sha256"
	"encoding/json"
	"flag"
	"fmt"
	"os"

	bvh "example.org/scp/bvhcontract"
)

const expectedSourceHash = "ab3a0d712c9c4f21fba0cf0698568dd5f88f1b959cf8aae28173c6435153d760"

func main() {
	src := flag.String("source", "", "original synthetic BVH")
	out := flag.String("out", "", "new source-safe projection JSON")
	caps := flag.Bool("capabilities", false, "read only capability discovery")
	flag.Parse()
	if *caps {
		fmt.Println("{\"schema\":\"scp.r009.original-bvh-ordered-quaternion-loss.v1\",\"actions\":[\"capabilities\",\"export_original_source_only\"],\"private_R009\":\"HELD_NOT_ACCEPTED\",\"physical_retarget\":\"NOT_RUN\"}")
		return
	}
	fail := func(c string) { fmt.Fprintln(os.Stderr, "BVH_QUATERNION_SOURCE_REJECT:"+c); os.Exit(2) }
	if *src == "" || *out == "" || len(flag.Args()) != 0 || *src == *out {
		fail("MISSING_OR_ALIASED_INPUT_OUTPUT")
	}
	raw, e := os.ReadFile(*src)
	if e != nil {
		fail("UNREADABLE_SOURCE")
	}
	if fmt.Sprintf("%x", sha256.Sum256(raw)) != expectedSourceHash {
		fail("UNADMITTED_SOURCE_SHA")
	}
	m, e := bvh.Parse(raw, "ORIGINAL_SELF_AUTHORED_SYNTHETIC", 1.)
	if e != nil {
		fail("SOURCE_PARSER_REJECT")
	}
	res, e := m.SourceSynthetic60To30()
	if e != nil {
		fail("NON_60_TO_30_SOURCE")
	}
	if res.ProtectedR009 != "HELD_NOT_ACCEPTED" || res.HumanROM != "UNKNOWN" || res.PhysicalRetarget != "NOT_RUN_SOURCE_QUATERNIONS_ONLY" {
		fail("FALSE_BIOLOGICAL_OR_PROTECTED_CLAIM")
	}
	data, e := json.MarshalIndent(res, "", "  ")
	if e != nil {
		fail("SOURCE_JSON_MARSHAL")
	}
	if _, e = os.Stat(*out); e == nil {
		fail("NO_OVERWRITE")
	}
	f, e := os.OpenFile(*out, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if e != nil {
		fail("NO_CREATE_OR_OVERWRITE")
	}
	if _, e = f.Write(append(data, 10)); e != nil {
		_ = f.Close()
		_ = os.Remove(*out)
		fail("WRITE_FAILED")
	}
	if e = f.Close(); e != nil {
		_ = os.Remove(*out)
		fail("CLOSE_FAILED")
	}
	fmt.Printf("PASS_ORIGINAL_SYNTHETIC_BVH_ORDERED_QUATERNION_SOURCE_ONLY sha256=%x keys=%d\n", sha256.Sum256(raw), len(res.Keyframes))
}
