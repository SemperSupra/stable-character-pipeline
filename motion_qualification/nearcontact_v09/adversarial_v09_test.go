package motion

import (
	"math"
	"testing"
)

// Independent falsifier: exact rational frame time MUST distinguish adjacent
// samples even when frame indices are much larger than float64's 53-bit mantissa.
func TestAdversarialLargeTickClockCollapse(t *testing.T) {
	a := Timestamp{Tick: 1 << 60, FPSNum: 30, FPSDen: 1}
	b := Timestamp{Tick: (1 << 60) + 1, FPSNum: 30, FPSDen: 1}
	if Synchronized(a, b, 0) {
		t.Fatal("FALSE_ACCEPT: adjacent 30fps samples collapsed at large ticks")
	}
}

func TestAdversarialPairEpipolarNaNFailsClosed(t *testing.T) {
	l, r := observe(0, 4)
	l.Y = math.NaN()
	got := (Stereo{800, .4}).Associate([2]Detection{l, l}, [2]Detection{r, r}, [2]Prior{{0, 4}, {0, 4}}, 1, .1)
	if got.Status != Reject {
		t.Fatalf("untrusted NaN epipolar y was not rejected: %s", got.Status)
	}
}
