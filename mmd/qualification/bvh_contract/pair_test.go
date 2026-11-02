package bvh

import (
	"strings"
	"testing"
)

func TestPairedClockNoInventedHumanAdmissibility(t *testing.T) {
	a := must(t, originalFixture)
	b := must(t, strings.Replace(originalFixture, "1 0 0 0 0 0 0 0 0 0 0 0", "2 0 0 0 0 0 0 0 0 0 0 0", 1))
	r, e := CheckPair(a, b)
	if e != nil {
		t.Fatal(e)
	}
	if r.SynchronizedTake || r.Status != "CLOCK_COMPATIBLE_ORIGINAL_SYNTHETIC_ONLY_SESSION_SYNC_UNKNOWN" || r.PrivateR009 != "HELD_NOT_ADMITTED" {
		t.Fatal("false human acceptance")
	}
	if r.ActorAHash == r.ActorBHash {
		t.Fatal("duplicate actor source bytes")
	}
	if _, e = CheckPair(a, a); e == nil {
		t.Fatal("same source as distinct actor accepted")
	}
	b.FrameTimeSeconds = "1/30"
	if _, e = CheckPair(a, b); e == nil {
		t.Fatal("mismatched source clock accepted")
	}
}
func TestPairedLengthMismatchRejected(t *testing.T) {
	a := must(t, originalFixture)
	b := must(t, strings.Replace(originalFixture, "1 0 0 0 0 0 0 0 0 0 0 0", "2 0 0 0 0 0 0 0 0 0 0 0", 1))
	b.Frames = b.Frames[:2]
	if _, e := CheckPair(a, b); e == nil {
		t.Fatal("unmatched captured duration accepted")
	}
}
