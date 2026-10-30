package motion

import "testing"

// Negative scientific result, NOT a positive identity acceptance test:
// an internally self-consistent but false prior can drive an unequivocally
// incorrect cross-camera association even with a small reported pixel sigma.
func TestAdversarialFalsePriorWitness(t *testing.T) {
	var left, right [2]Detection
	left[0], right[0] = observe(-.05, 4)
	left[1], right[1] = observe(.05, 4)
	// These are the geometries of the WRONG swapped camera pairing, not
	// independent observations of either real synthetic actor.
	forged := [2]Prior{{0, 16.0 / 3.0}, {0, 16.0 / 5.0}}
	got := (Stereo{800, .4}).AssociateWithNoiseWitness(left, right, forged, 2, .15, .1, 3)
	if got.Status != Accept || got.Pairs[0].RightIndex != 1 || got.Pairs[1].RightIndex != 0 {
		t.Fatalf("original false-prior negative changed; adjudicate anew: %+v", got)
	}
	t.Log("RED_SCIENTIFIC_FALSE_PRIOR: accepted two WRONG identities under fabricated but internally consistent prior")
}

// A wrong stereo focal length can appear valid if the source prior is derived
// from that SAME wrong calibration. Independent source-scale evidence is
// necessary; a self-derived prior is not an independent calibration witness.
func TestAdversarialWrongFocalSelfConsistentPrior(t *testing.T) {
	var left, right [2]Detection
	left[0], right[0] = observe(0, 4)
	left[1], right[1] = observe(0, 8)
	biased := Stereo{850, .4}
	got := biased.AssociateWithNoiseWitness(left, right, [2]Prior{{0, 4.25}, {0, 8.5}}, .2, .1, .1, 3)
	if got.Status != Accept || got.Pairs[0].RightIndex != 0 || got.Pairs[1].RightIndex != 1 {
		t.Fatalf("original self-consistent wrong-focal negative changed: %+v", got)
	}
	if status := biased.ScaleWitness(left, right, 4, .02); status != Reject {
		t.Fatalf("independent known-distance witness did not reject wrong focal: %s", status)
	}
	t.Log("RED_SCIENTIFIC_BAD_CALIBRATION: wrong focal accepted without independent scale witness")
}
