package bvh

import (
	"fmt"
	"math"
	"strings"
	"testing"
)

const originalFixture = `HIERARCHY
ROOT Hips {
 OFFSET 0 0 0
 CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation
 JOINT Knee {
  OFFSET 0 -1 0
  CHANNELS 3 Zrotation Xrotation Yrotation\n  JOINT Foot {
   OFFSET 0 -1 0
   CHANNELS 3 Zrotation Xrotation Yrotation
   End Site { OFFSET 0 -0.1 0 }
  }
 }
}
MOTION
Frames: 3
Frame Time: 0.016666666666666667
0 0 0 0 0 0 0 0 0 0 0 0
0.5 0 0 90 0 0 0 0 0 0 0 0
1 0 0 0 0 0 0 0 0 0 0 0
`

func must(t *testing.T, s string) *Motion {
	t.Helper()
	m, e := Parse([]byte(s), "ORIGINAL_SELF_AUTHORED_SYNTHETIC", 1)
	if e != nil {
		t.Fatal(e)
	}
	return m
}
func closeVec(a Vec3, x, y, z float64) bool {
	return math.Abs(a[0]-x) < 1e-8 && math.Abs(a[1]-y) < 1e-8 && math.Abs(a[2]-z) < 1e-8
}
func TestTrueSourceOrderedFKAndClock(t *testing.T) {
	m := must(t, originalFixture)
	if m.FrameTimeSeconds != "16666666666666667/1000000000000000000" {
		t.Fatalf("exact parsed decimal rational %s", m.FrameTimeSeconds)
	}
	if len(m.Joints) != 3 || len(m.Frames) != 3 {
		t.Fatalf("unexpected shape")
	}
	w, e := m.Evaluate(1)
	if e != nil {
		t.Fatal(e)
	}
	if !closeVec(w[0].PositionMeters, .5, 0, 0) || !closeVec(w[1].PositionMeters, 1.5, 0, 0) || !closeVec(w[2].PositionMeters, 2.5, 0, 0) {
		t.Fatalf("incorrect Z rotation FK %+v", w)
	}
	w, e = m.Evaluate(0)
	if e != nil {
		t.Fatal(e)
	}
	if !closeVec(w[2].PositionMeters, 0, -2, 0) {
		t.Fatal(w)
	}
}
func TestUnitsNotInferred(t *testing.T) {
	m, e := Parse([]byte(originalFixture), "ORIGINAL_SELF_AUTHORED_SYNTHETIC", .05)
	if e != nil {
		t.Fatal(e)
	}
	w, e := m.Evaluate(1)
	if e != nil {
		t.Fatal(e)
	}
	if !closeVec(w[2].PositionMeters, .125, 0, 0) {
		t.Fatal(w)
	}
	if _, e = Parse([]byte(originalFixture), "UNKNOWN_SOURCE", 1); e == nil {
		t.Fatal("rights missing accepted")
	}
	if _, e = Parse([]byte(originalFixture), "ORIGINAL_SELF_AUTHORED_SYNTHETIC", 0); e == nil {
		t.Fatal("unit missing accepted")
	}
}
func TestStrictAdversarialControls(t *testing.T) {
	cases := map[string]string{
		"wrong_frame_budget": strings.Replace(originalFixture, "Frames: 3", "Frames: 4", 1),
		"extra_channel":      originalFixture + "0",
		"duplicate_node":     strings.Replace(originalFixture, "JOINT Foot", "JOINT Knee", 1),
		"nonfinite_frame":    strings.Replace(originalFixture, "0.5 0 0", "NaN 0 0", 1),
		"unknown_channel":    strings.Replace(originalFixture, "Zrotation Xrotation Yrotation\n  JOINT Foot", "Zrotation Xrotation Unknown\n  JOINT Foot", 1),
		"duplicate_channel":  strings.Replace(originalFixture, "Zrotation Xrotation Yrotation\n  JOINT Foot", "Zrotation Xrotation Zrotation\n  JOINT Foot", 1),
		"unbounded_size":     originalFixture + strings.Repeat("X", MaxBytes),
		"bad_frame_time":     strings.Replace(originalFixture, "Frame Time: 0.016666666666666667", "Frame Time: 0", 1),
		"missing_brace":      strings.Replace(originalFixture, "End Site { OFFSET 0 -0.1 0 }", "End Site { OFFSET 0 -0.1 0", 1),
	}
	for name, s := range cases {
		t.Run(name, func(t *testing.T) {
			if _, e := Parse([]byte(s), "ORIGINAL_SELF_AUTHORED_SYNTHETIC", 1); e == nil {
				t.Fatal("false PASS " + name)
			}
		})
	}
}
func TestReproductionAndPairedClock(t *testing.T) {
	a := must(t, originalFixture)
	b := must(t, originalFixture)
	if a.SourceSHA256 != b.SourceSHA256 {
		t.Fatal("repro SHA mismatched")
	}
	b.FrameTimeSeconds = "1/30"
	if a.FrameTimeSeconds == b.FrameTimeSeconds {
		t.Fatal("source clock must not silently alias")
	}
	for i := 0; i < 3; i++ {
		x, _ := a.Evaluate(i)
		y, _ := must(t, originalFixture).Evaluate(i)
		for k := range x {
			if fmt.Sprint(x[k]) != fmt.Sprint(y[k]) {
				t.Fatal("non-deterministic original FK")
			}
		}
	}
}
