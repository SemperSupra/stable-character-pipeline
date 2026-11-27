package main

import (
	"reflect"
	"testing"

	rendercontract "example.org/synthetic/rendercontract"
)

func TestR171SyntheticFactorIsolation(t *testing.T) {
	base, err := rendercontract.Canonicalize(makeRequest("A"))
	if err != nil {
		t.Fatal(err)
	}
	baseHash, err := rendercontract.Fingerprint(base)
	if err != nil {
		t.Fatal(err)
	}
	controls := []struct {
		variant                     string
		camera, material, light bool
	}{
		{"camera", true, false, false},
		{"material", false, true, false},
		{"light", false, false, true},
		{"B", true, true, true},
	}
	for _, c := range controls {
		t.Run(c.variant, func(t *testing.T) {
			next, err := rendercontract.Canonicalize(makeRequest(c.variant))
			if err != nil {
				t.Fatal(err)
			}
			if !reflect.DeepEqual(base.Source, next.Source) ||
				!reflect.DeepEqual(base.Objects, next.Objects) ||
				!reflect.DeepEqual(base.Options, next.Options) {
				t.Fatal("factor changed synthetic source/geometry identity or render settings")
			}
			if got := !reflect.DeepEqual(base.Cameras, next.Cameras); got != c.camera {
				t.Errorf("camera delta got %v want %v", got, c.camera)
			}
			if got := !reflect.DeepEqual(base.Materials, next.Materials); got != c.material {
				t.Errorf("material delta got %v want %v", got, c.material)
			}
			if got := !reflect.DeepEqual(base.Lights, next.Lights); got != c.light {
				t.Errorf("light delta got %v want %v", got, c.light)
			}
			digest, err := rendercontract.Fingerprint(next)
			if err != nil {
				t.Fatal(err)
			}
			if digest == baseHash {
				t.Fatal("isolated factor changed but request digest did not")
			}
		})
	}
}
