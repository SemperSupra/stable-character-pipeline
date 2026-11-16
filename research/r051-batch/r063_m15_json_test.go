// Model-proposed public synthetic fixture cases; deterministic source renderer.
package main

import (
	"fmt"
	"os"
	"testing"
)

func TestR063M15Json(t *testing.T) {
	cases := []struct {
		Input  string
		Reject bool
	}{
		{"{\"schema\":\"scp.r051.batch-rep.v1\"}", false},
		{"{}", false},
		{"{\"schema\":1,\"schema\":2}", true},
		{"{\"unknown\":\"field\"}", true},
	}
	for i, tc := range cases {
		t.Run(fmt.Sprintf("case-%d", i), func(t *testing.T) {
			p := t.TempDir() + "/fixture.json"
			if err := os.WriteFile(p, []byte(tc.Input), 0600); err != nil {
				t.Fatal(err)
			}
			var parsed Batch
			err := decodeLocalBounded(p, &parsed)
			if tc.Reject && err == nil {
				t.Errorf("input %q must be rejected", tc.Input)
			}
			if !tc.Reject && err != nil {
				t.Errorf("input %q unexpectedly rejected: %v", tc.Input, err)
			}
		})
	}
}
