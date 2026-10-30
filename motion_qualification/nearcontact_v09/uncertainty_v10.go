package motion

import "math"

// AssociateWithNoiseWitness is original synthetic research: noiseSigmaPixels
// MUST be an independently calibrated per-detection uncertainty witness.
// This screen does not establish real person identity or source-native tracking.
func (s Stereo) AssociateWithNoiseWitness(left, right [2]Detection, prior [2]Prior, maxErrorMeters, minCostGap, noiseSigmaPixels, sigmaMultiplier float64) Result {
	bad := Result{Status: Reject}
	if !finite(noiseSigmaPixels, sigmaMultiplier) || noiseSigmaPixels < 0 || sigmaMultiplier < 3 || sigmaMultiplier > 20 || s.validate() != nil {
		return bad
	}
	base := s.Associate(left, right, prior, maxErrorMeters, minCostGap)
	if base.Status != Accept || noiseSigmaPixels == 0 {
		return base
	}
	// Two independently noisy pixels have difference sigma = sqrt(2)*sigma.
	// A >=3-sigma witness in both observed and predicted camera projections
	// must exist before identity assignment can be accepted.
	minSep := math.Sqrt2 * sigmaMultiplier * noiseSigmaPixels
	if !finite(left[0].X, left[1].X, right[0].X, right[1].X) {
		return bad
	}
	if math.Abs(left[0].X-left[1].X) <= minSep || math.Abs(right[0].X-right[1].X) <= minSep {
		return Result{Status: Abstain}
	}
	for _, shift := range []float64{s.BaselineMeters / 2, -s.BaselineMeters / 2} {
		pred0 := s.FocalPixels * (prior[0].X + shift) / prior[0].Z
		pred1 := s.FocalPixels * (prior[1].X + shift) / prior[1].Z
		if !finite(pred0, pred1) || math.Abs(pred0-pred1) <= minSep {
			return Result{Status: Abstain}
		}
	}
	return base
}
