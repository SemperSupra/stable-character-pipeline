package main

import (
	"math"
	"reflect"
	"testing"
)

func TestDeterminism(t *testing.T) {
	a, r := Simulate()
	b, s := Simulate()
	if !reflect.DeepEqual(r, s) {
		t.Fatal("non deterministic receipt")
	}
	if len(a) != len(b) || len(a) != 169 {
		t.Fatal("wrong count")
	}
	for i := range a {
		if a[i] != b[i] {
			t.Fatalf("nondeterministic frame %d", i)
		}
	}
}
func TestGroundContactAndIK(t *testing.T) {
	frames, r := Simulate()
	if r.Status != "PASS_TRAJECTORY_AND_CONTACT_PROOF_ONLY" {
		t.Fatalf("HOLD: %+v", r)
	}
	if r.MaxFootSlipM > 1e-8 {
		t.Fatal("sliding planted foot")
	}
	if r.MinGroundHeightM < 0 {
		t.Fatal("foot below floor")
	}
	for _, f := range frames {
		for _, leg := range []LegFrame{f.Left, f.Right} {
			if math.Abs(leg.Hip.Sub(leg.Knee).Norm()-UpperLeg) > 1e-5 {
				t.Fatalf("upper link incorrect %d", f.Number)
			}
			if math.Abs(leg.Knee.Sub(leg.Ankle).Norm()-LowerLeg) > 1e-5 {
				t.Fatalf("lower link incorrect %d", f.Number)
			}
		}
	}
}
func TestRequiredPhases(t *testing.T) {
	frames, _ := Simulate()
	phases := map[string]bool{}
	for _, f := range frames {
		phases[f.Phase] = true
	}
	for _, p := range []string{"start", "walk", "turn", "stop", "stand"} {
		if !phases[p] {
			t.Fatalf("missing %s", p)
		}
	}
	if math.Abs(frames[len(frames)-1].Yaw-math.Pi/3) > 1e-6 {
		t.Fatal("turn incorrect")
	}
}
func TestNoAutomatedVideoAdmission(t *testing.T) {
	_, r := Simulate()
	if len(r.Limitations) < 3 || r.Status == "PHOTOREAL_VIDEO_ACCEPTED" {
		t.Fatal("incorrect promotion")
	}
}
