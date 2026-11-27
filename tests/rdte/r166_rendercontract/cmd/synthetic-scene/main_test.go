package main

import (
	"reflect"
	"testing"

	rendercontract "example.org/synthetic/rendercontract"
)

func TestQualityProfilesPreserveScene(t *testing.T) {
	base := makeRequest("A")
	profiles := []struct {
		name                   string
		width, height, samples int
	}{
		{"preview", 160, 120, 8},
		{"standard", 320, 240, 32},
		{"quality", 640, 480, 64},
	}
	fingerprints := map[string]bool{}
	for _, p := range profiles {
		req := makeRequest("A")
		var err error
		req.Options, err = qualityOptions(p.name, req.Options)
		if err != nil {
			t.Fatal(err)
		}
		if req.Options.Width != p.width || req.Options.Height != p.height || req.Options.Samples != p.samples {
			t.Fatalf("bad profile: %+v", req.Options)
		}
		if req.Options.Engine != base.Options.Engine || req.Options.Seed != base.Options.Seed {
			t.Fatal("profile changed engine or seed")
		}
		digest, err := rendercontract.Fingerprint(req)
		if err != nil || fingerprints[digest] {
			t.Fatalf("invalid or repeated digest: %q %v", digest, err)
		}
		fingerprints[digest] = true
		req.Options = base.Options
		if !reflect.DeepEqual(req, base) {
			t.Fatal("quality profile changed non-render source")
		}
	}
}

func TestProfileArguments(t *testing.T) {
	v, p, err := parseArgs(nil)
	if err != nil || v != "A" || p != "standard" {
		t.Fatalf("bad defaults: %q %q %v", v, p, err)
	}
	v, p, err = parseArgs([]string{"--profile=quality", "--variant=B"})
	if err != nil || v != "B" || p != "quality" {
		t.Fatalf("bad options: %q %q %v", v, p, err)
	}
	for _, args := range [][]string{
		{"--profile=unknown"},
		{"--profile=preview", "--profile=quality"},
		{"--variant=A", "--variant=B"},
		{"--variant=C"},
		{"--samples=1000000"},
	} {
		if _, _, err := parseArgs(args); err == nil {
			t.Fatalf("accepted invalid arguments: %v", args)
		}
	}
}
