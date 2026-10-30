package motion

import (
	"encoding/json"
	"math"
	"testing"
)

func observe(x, z float64) (Detection, Detection) {
	f, b := 800., .4
	return Detection{X: f * (x + b/2) / z, Y: 100}, Detection{X: f * (x - b/2) / z, Y: 100}
}
func TestClearAssignmentAccepted(t *testing.T) {
	var l, r [2]Detection
	l[0], r[0] = observe(-1.5, 4)
	l[1], r[1] = observe(1.5, 4)
	got := (Stereo{800, .4}).Associate(l, r, [2]Prior{{-1.5, 4}, {1.5, 4}}, 2, .15)
	if got.Status != Accept || got.Pairs[0].RightIndex != 0 || got.Pairs[1].RightIndex != 1 {
		t.Fatalf("%+v", got)
	}
}
func TestAmbiguousNearContactAbstains(t *testing.T) {
	var l, r [2]Detection
	l[0], r[0] = observe(-.001, 4)
	l[1], r[1] = observe(.001, 4)
	got := (Stereo{800, .4}).Associate(l, r, [2]Prior{{0, 4}, {0, 4}}, 1, .15)
	if got.Status != Abstain {
		t.Fatalf("ambiguous pair wrongly admitted: %+v", got)
	}
}
func TestInvalidDisparityRejects(t *testing.T) {
	_, e := (Stereo{800, .4}).Triangulate(Detection{X: 4}, Detection{X: 4})
	if e == nil {
		t.Fatal("zero disparity")
	}
	_, e = (Stereo{800, .4}).Triangulate(Detection{X: math.NaN()}, Detection{X: 0})
	if e == nil {
		t.Fatal("NaN")
	}
}
func TestWrongClockRejects(t *testing.T) {
	if Synchronized(Timestamp{10, 30, 1}, Timestamp{11, 30, 1}, .010) {
		t.Fatal("one frame delay accepted")
	}
	if !Synchronized(Timestamp{60, 60, 1}, Timestamp{30, 30, 1}, 1e-9) {
		t.Fatal("exact rational timestamp mismatch")
	}
}
func TestWrongFocalRequiresScaleWitness(t *testing.T) {
	// x=0,z=4 and x=0,z=8; true separation 4m; applying focal 850 instead
	// of 800 scales depth by 6.25%, requiring independent length witness.
	var l, r [2]Detection
	l[0], r[0] = observe(0, 4)
	l[1], r[1] = observe(0, 8)
	if got := (Stereo{850, .4}).ScaleWitness(l, r, 4, .02); got != Reject {
		t.Fatalf("wrong focal: %s", got)
	}
	if got := (Stereo{850, .4}).ScaleWitness(l, r, 0, .02); got != Unknown {
		t.Fatalf("missing witness: %s", got)
	}
	if got := (Stereo{800, .4}).ScaleWitness(l, r, 4, .02); got != Accept {
		t.Fatalf("correct witness: %s", got)
	}
}
func TestSwappedCameraCoordinatesReject(t *testing.T) {
	l, r := observe(0, 4)
	_, err := (Stereo{800, .4}).Triangulate(r, l)
	if err == nil {
		t.Fatal("mirrored disparity accepted")
	}
}

func TestMachineReceiptJSON(t *testing.T) {
	var l, r [2]Detection
	l[0], r[0] = observe(-1.5, 4)
	l[1], r[1] = observe(1.5, 4)
	got := (Stereo{800, .4}).Associate(l, r, [2]Prior{{-1.5, 4}, {1.5, 4}}, 2, .15)
	if _, err := json.Marshal(got); err != nil {
		t.Fatalf("nonfinite machine result: %v", err)
	}
}
