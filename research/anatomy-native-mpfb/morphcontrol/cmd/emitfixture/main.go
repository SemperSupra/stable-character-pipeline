// Command emitfixture creates an immutable, original-synthetic, source-safe
// canonical morph transaction payload for an independent Godot runtime probe.
// No secret, real identity data or network endpoints. No external libraries.
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"

	ctl "github.com/SemperSupra/stable-character-pipeline/research/anatomy-native-mpfb/morphcontrol"
)

func main() {
	out := flag.String("out", "", "disposable Godot project root")
	flag.Parse()
	if *out == "" {
		fmt.Fprintln(os.Stderr, "R049_HOLD missing isolated output path")
		os.Exit(12)
	}
	if err := os.MkdirAll(*out, 0700); err != nil {
		panic(err)
	}
	vals := make(map[string]float64, len(ctl.Channels))
	for i, key := range ctl.Channels {
		vals[key] = float64(i+1) / 20.0
	}
	controller := ctl.New()
	plan, err := controller.Prepare(0, vals)
	if err != nil {
		panic(err)
	}
	payload, err := json.Marshal(struct {
		Schema           string      `json:"schema"`
		ExpectedRevision uint64      `json:"expected_revision"`
		Sequence         []ctl.Entry `json:"sequence"`
	}{Schema: plan.Schema, ExpectedRevision: plan.ExpectedRevision, Sequence: plan.Sequence})
	if err != nil {
		panic(err)
	}
	hashed := sha256.Sum256(payload)
	sha := hex.EncodeToString(hashed[:])
	if sha != plan.SHA256 {
		panic("R049_HOLD prepared Go plan digest mismatched raw canonical payload")
	}
	if len(plan.Sequence) != 24 {
		panic("R049_HOLD incorrect command count")
	}
	if err := os.WriteFile(filepath.Join(*out, "payload.json"), payload, 0600); err != nil {
		panic(err)
	}
	if err := os.WriteFile(filepath.Join(*out, "sha256.txt"), []byte(sha+string(rune(10))), 0600); err != nil {
		panic(err)
	}
	// Negative control is an integrity-only mutation with UNCHANGED digest.
	altered := append([]byte(nil), payload...)
	for i := range altered {
		if altered[i] == '3' {
			altered[i] = '4'
			break
		}
	}
	if sha256.Sum256(altered) == hashed {
		panic("R049_HOLD mutation failed to invalidate canonical digest")
	}
	if err := os.WriteFile(filepath.Join(*out, "tampered.json"), altered, 0600); err != nil {
		panic(err)
	}
	fmt.Println(fmt.Sprintf("R049_GO_PREPARED_RECEIPT status=PASS_CANONICAL_PLAN_FOR_ENGINE_ADAPTER commands=%d sha256=%s nonce=NONE expected_revision=%d godot_applied=NO", len(plan.Sequence), sha, plan.ExpectedRevision))
}
