// Model-proposed public synthetic fixture cases; deterministic source renderer.
package main

import (
	"fmt"
	"testing"
)

func TestR063M15Path(t *testing.T) {
	cases := []struct {
		Input  string
		Reject bool
	}{
		{"src/good", false},
		{"src/good/**", false},
		{"/abs/path/to/file", true},
		{"\\backslashes\\path\\to\\file", true},
	}
	for i, tc := range cases {
		t.Run(fmt.Sprintf("case-%d", i), func(t *testing.T) {
			err := cleanPath(tc.Input)
			if tc.Reject && err == nil {
				t.Errorf("input %q must be rejected", tc.Input)
			}
			if !tc.Reject && err != nil {
				t.Errorf("input %q unexpectedly rejected: %v", tc.Input, err)
			}
		})
	}
}
