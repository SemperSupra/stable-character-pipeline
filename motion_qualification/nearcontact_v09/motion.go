// Package motion provides original, purely synthetic cross-camera association
// and geometry negative controls. It is not an image tracker or real rig solver.
package motion

import (
	"errors"
	"math"
	"math/big"
)

type Status string

const (
	Accept  Status = "ACCEPT_SYNTHETIC"
	Abstain Status = "ABSTAIN_AMBIGUOUS"
	Reject  Status = "REJECT_INVALID"
	Unknown Status = "UNKNOWN_NO_SCALE_WITNESS"
)

type Detection struct{ X, Y float64 }
type Prior struct{ X, Z float64 }
type Stereo struct{ FocalPixels, BaselineMeters float64 }
type Pair struct {
	X, Z                  float64
	LeftIndex, RightIndex int
}
type Result struct {
	Status           Status
	Pairs            [2]Pair
	BestCost, Margin float64
}

func finite(xs ...float64) bool {
	for _, v := range xs {
		if math.IsNaN(v) || math.IsInf(v, 0) {
			return false
		}
	}
	return true
}
func (s Stereo) validate() error {
	if !finite(s.FocalPixels, s.BaselineMeters) || s.FocalPixels <= 0 || s.BaselineMeters <= 0 {
		return errors.New("invalid stereo calibration")
	}
	return nil
}
func (s Stereo) Triangulate(l, r Detection) (Pair, error) {
	if err := s.validate(); err != nil {
		return Pair{}, err
	}
	if !finite(l.X, l.Y, r.X, r.Y) {
		return Pair{}, errors.New("invalid pixel")
	}
	// Two identical parallel cameras with shared principal point; camera centers are ±B/2.
	d := l.X - r.X
	if d <= 0 {
		return Pair{}, errors.New("invalid disparity")
	}
	z := s.FocalPixels * s.BaselineMeters / d
	x := (l.X + r.X) * z / (2 * s.FocalPixels)
	if !finite(z, x) || z <= 0 {
		return Pair{}, errors.New("invalid 3d point")
	}
	return Pair{X: x, Z: z}, nil
}

// Associate enumerates both bijections, never treating camera-association as
// observed identity. Rejects if geometry, prior, or an ambiguity margin fails.
func (s Stereo) Associate(left, right [2]Detection, prior [2]Prior, maxErrorMeters, minCostGap float64) Result {
	bad := Result{Status: Reject}
	if s.validate() != nil || !finite(maxErrorMeters, minCostGap) || maxErrorMeters <= 0 || minCostGap <= 0 {
		return bad
	}
	for _, p := range prior {
		if !finite(p.X, p.Z) || p.Z <= 0 {
			return bad
		}
	}
	var choices [2]struct {
		p     [2]Pair
		cost  float64
		valid bool
	}
	for perm := 0; perm < 2; perm++ {
		valid := true
		cost := 0.
		var pairs [2]Pair
		for i := 0; i < 2; i++ {
			j := i
			if perm == 1 {
				j = 1 - i
			}
			p, e := s.Triangulate(left[i], right[j])
			if e != nil {
				valid = false
				break
			}
			// With parallel cameras, epipolar y agreement must be explicitly checked.
			if math.Abs(left[i].Y-right[j].Y) > 3 {
				valid = false
				break
			}
			p.LeftIndex = i
			p.RightIndex = j
			pairs[i] = p
			dx, dz := p.X-prior[i].X, p.Z-prior[i].Z
			dist := math.Hypot(dx, dz)
			if dist > maxErrorMeters {
				valid = false
				break
			}
			cost += dist
		}
		choices[perm] = struct {
			p     [2]Pair
			cost  float64
			valid bool
		}{pairs, cost, valid}
	}
	if !choices[0].valid && !choices[1].valid {
		return bad
	}
	if choices[0].valid != choices[1].valid {
		j := 0
		if choices[1].valid {
			j = 1
		}
		return Result{Status: Accept, Pairs: choices[j].p, BestCost: choices[j].cost, Margin: 0}
	}
	best, runner := 0, 1
	if choices[1].cost < choices[0].cost {
		best, runner = 1, 0
	}
	margin := choices[runner].cost - choices[best].cost
	if margin < minCostGap {
		return Result{Status: Abstain, BestCost: choices[best].cost, Margin: margin}
	}
	return Result{Status: Accept, Pairs: choices[best].p, BestCost: choices[best].cost, Margin: margin}
}

type Timestamp struct{ Tick, FPSNum, FPSDen int64 }

func (t Timestamp) seconds() (float64, error) {
	if t.Tick < 0 || t.FPSNum <= 0 || t.FPSDen <= 0 {
		return 0, errors.New("invalid timestamp")
	}
	return float64(t.Tick) * float64(t.FPSDen) / float64(t.FPSNum), nil
}
func Synchronized(a, b Timestamp, maxDeltaSec float64) bool {
	if a.Tick < 0 || b.Tick < 0 || a.FPSNum <= 0 || b.FPSNum <= 0 || a.FPSDen <= 0 || b.FPSDen <= 0 || !finite(maxDeltaSec) || maxDeltaSec < 0 {
		return false
	}
	// Fractional frame timestamps must not collapse at high tick counts.
	makeTime := func(t Timestamp) *big.Rat {
		v := new(big.Int).Mul(big.NewInt(t.Tick), big.NewInt(t.FPSDen))
		return new(big.Rat).SetFrac(v, big.NewInt(t.FPSNum))
	}
	delta := new(big.Rat).Sub(makeTime(a), makeTime(b))
	delta.Abs(delta)
	limit := new(big.Rat).SetFloat64(maxDeltaSec)
	return limit != nil && delta.Cmp(limit) <= 0
}

// ScaleWitness requires measured independently known anchor separation. Without
// it, a wrong focal length can be internally self-consistent in stereo.
func (s Stereo) ScaleWitness(left, right [2]Detection, knownDistanceMeters, toleranceRatio float64) Status {
	if !finite(knownDistanceMeters, toleranceRatio) || toleranceRatio <= 0 {
		return Reject
	}
	if knownDistanceMeters <= 0 {
		return Unknown
	}
	p0, e0 := s.Triangulate(left[0], right[0])
	p1, e1 := s.Triangulate(left[1], right[1])
	if e0 != nil || e1 != nil {
		return Reject
	}
	measured := math.Hypot(p1.X-p0.X, p1.Z-p0.Z)
	if math.Abs(measured-knownDistanceMeters)/knownDistanceMeters > toleranceRatio {
		return Reject
	}
	return Accept
}
