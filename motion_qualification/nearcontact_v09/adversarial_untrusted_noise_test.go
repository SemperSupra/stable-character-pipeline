package motion

import (
	"math/rand"
	"testing"
)

// This deliberately false upstream confidence claim is a scientific negative.
// The wrapper alone cannot validate provenance or distribution of pixel noise.
func TestAdversarialUntrustedUncertaintyWitness(t *testing.T) {
	for _, seed := range []int64{20261102, 20261103, 20261104} {
		r := rand.New(rand.NewSource(seed))
		wrong, accepted, abstained, rejected := 0, 0, 0, 0
		for _, gap := range []float64{.02, .05, .1} {
			for k := 0; k < 1000; k++ {
				l0, r0 := observe(-gap, 4)
				l1, r1 := observe(gap, 4)
				l := [2]Detection{l0, l1}
				rr := [2]Detection{r0, r1}
				// Declared sigma 0.5px but true observations are heavy-tailed:
				// each camera+actor point has a 10% chance of sigma=6px.
				for i := 0; i < 2; i++ {
					sigma := .5
					if r.Float64() < .1 {
						sigma = 6
					}
					l[i].X += r.NormFloat64() * sigma
					l[i].Y += r.NormFloat64() * sigma
					sigma = .5
					if r.Float64() < .1 {
						sigma = 6
					}
					rr[i].X += r.NormFloat64() * sigma
					rr[i].Y += r.NormFloat64() * sigma
				}
				truth := [2]int{0, 1}
				if k%2 == 1 {
					rr[0], rr[1] = rr[1], rr[0]
					truth = [2]int{1, 0}
				}
				out := (Stereo{800, .4}).AssociateWithNoiseWitness(l, rr, [2]Prior{{-gap, 4}, {gap, 4}}, .8, .15, .5, 3)
				switch out.Status {
				case Accept:
					accepted++
					if out.Pairs[0].RightIndex != truth[0] || out.Pairs[1].RightIndex != truth[1] {
						wrong++
					}
				case Abstain:
					abstained++
				case Reject:
					rejected++
				default:
					t.Fatalf("unrecognized synthetic status %s", out.Status)
				}
			}
		}
		t.Logf("HOSTILE_WITNESS seed=%d trials=3000 accepted=%d wrong=%d abstained=%d rejected=%d", seed, accepted, wrong, abstained, rejected)
		// A scientifically useful hostile negative must demonstrate this
		// untrusted witness does not qualify real-world identity admission.
		if wrong == 0 {
			t.Fatal("negative no longer exposes an untrusted witness")
		}
	}
}
