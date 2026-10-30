package motion

import (
	"math/rand"
	"testing"
)

func TestNoiseWitnessAdmissionControls(t *testing.T) {
	var l, r [2]Detection
	l[0], r[0] = observe(-.02, 4)
	l[1], r[1] = observe(.02, 4)
	pri := [2]Prior{{-.02, 4}, {.02, 4}}
	if got := (Stereo{800, .4}).AssociateWithNoiseWitness(l, r, pri, .8, .15, 2, 3); got.Status != Abstain {
		t.Fatalf("near-contact 2px uncertainty wrongly admitted: %+v", got)
	}
	l[0], r[0] = observe(-1.5, 4)
	l[1], r[1] = observe(1.5, 4)
	pri = [2]Prior{{-1.5, 4}, {1.5, 4}}
	if got := (Stereo{800, .4}).AssociateWithNoiseWitness(l, r, pri, .8, .15, 2, 3); got.Status != Accept {
		t.Fatalf("separated clean case incorrectly abstained: %+v", got)
	}
	if got := (Stereo{800, .4}).AssociateWithNoiseWitness(l, r, pri, .8, .15, -1, 3); got.Status != Reject {
		t.Fatal("negative uncertainty accepted")
	}
	if got := (Stereo{800, .4}).AssociateWithNoiseWitness(l, r, pri, .8, .15, 2, 1); got.Status != Reject {
		t.Fatal("underconfident multiplier accepted")
	}
}

// Fresh original synthetic trials; source v0.8 is NOT available for head-to-head.
// Final seeds 20261031/20261101 were reserved from the initial exploratory seed.
func TestIndependentSeededUncertaintyEnvelope(t *testing.T) {
	for _, seed := range []int64{20261030, 20261031, 20261101} {
		r := rand.New(rand.NewSource(seed))
		wrongBase, wrongGuard, acceptedBase, acceptedGuard, abstainBase, abstainGuard := 0, 0, 0, 0, 0, 0
		for _, gap := range []float64{.001, .005, .02, .1, 1.5} {
			for _, sigma := range []float64{0, .5, 2, 5} {
				for k := 0; k < 200; k++ {
					l0, r0 := observe(-gap, 4)
					l1, r1 := observe(gap, 4)
					l := [2]Detection{l0, l1}
					right := [2]Detection{r0, r1}
					for i := 0; i < 2; i++ {
						l[i].X += r.NormFloat64() * sigma
						l[i].Y += r.NormFloat64() * sigma
						right[i].X += r.NormFloat64() * sigma
						right[i].Y += r.NormFloat64() * sigma
					}
					truth := [2]int{0, 1}
					if k%2 == 1 {
						right[0], right[1] = right[1], right[0]
						truth = [2]int{1, 0}
					}
					pri := [2]Prior{{-gap, 4}, {gap, 4}}
					base := (Stereo{800, .4}).Associate(l, right, pri, .8, .15)
					guard := (Stereo{800, .4}).AssociateWithNoiseWitness(l, right, pri, .8, .15, sigma, 3)
					if base.Status == Accept {
						acceptedBase++
						if base.Pairs[0].RightIndex != truth[0] || base.Pairs[1].RightIndex != truth[1] {
							wrongBase++
						}
					}
					if guard.Status == Accept {
						acceptedGuard++
						if guard.Pairs[0].RightIndex != truth[0] || guard.Pairs[1].RightIndex != truth[1] {
							wrongGuard++
						}
					}
					if base.Status == Abstain {
						abstainBase++
					}
					if guard.Status == Abstain {
						abstainGuard++
					}
				}
			}
		}
		t.Logf("UNQUALIFIED_SYNTHETIC seed=%d trials=4000 base_accepted=%d base_wrong=%d base_abstain=%d guarded_accepted=%d guarded_wrong=%d guarded_abstain=%d", seed, acceptedBase, wrongBase, abstainBase, acceptedGuard, wrongGuard, abstainGuard)
		if wrongGuard != 0 {
			t.Errorf("RED: noise-witness screen wrong accepted seed=%d count=%d", seed, wrongGuard)
		}
	}
}
