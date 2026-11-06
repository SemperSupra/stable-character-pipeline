package main

import (
	"bytes"
	"encoding/json"
	"math"
	"testing"
)

func TestWindProbeSyntheticDeterminismAndDamping(t *testing.T) {
	for _, id := range []string{"triticum_aestivum", "zea_mays", "helianthus_annuus", "phyllostachys_aurea", "quercus_robur"} {
		s := loadExtendedPreset(t, id)
		p := SyntheticWindProfile(s)
		a, err := RunWindProbe(p)
		if err != nil {
			t.Fatalf("%s: %v", id, err)
		}
		if a.MaxAbsDisplacementM <= 0 || len(a.Samples) != 481 {
			t.Fatalf("%s unconvincing bounds: %d frames", id, len(a.Samples))
		}
		b, err := RunWindProbe(p)
		if err != nil {
			t.Fatal(err)
		}
		x, _ := json.Marshal(a)
		y, _ := json.Marshal(b)
		if !bytes.Equal(x, y) {
			t.Fatal("nondeterministic fixed-step trace")
		}
		p.WindMeanMPerS = 0
		p.GustAmplitudeMPerS = 0
		still, err := RunWindProbe(p)
		if err != nil {
			t.Fatal(err)
		}
		if still.MaxAbsDisplacementM != 0 || still.MaxAbsVelocityMPerS != 0 {
			t.Fatal("phantom wind response")
		}
	}
}
func TestWindProbeUnforcedDecayAndRejects(t *testing.T) {
	p := SyntheticWindProfile(loadExtendedPreset(t, "triticum_aestivum"))
	p.WindMeanMPerS = 0
	p.GustAmplitudeMPerS = 0
	p.InitialDisplacementM = .04
	r, err := RunWindProbe(p)
	if err != nil {
		t.Fatal(err)
	}
	if !(r.Samples[len(r.Samples)-1].MechanicalEnergyJ < r.Samples[0].MechanicalEnergyJ) {
		t.Fatal("damped plant gained energy without wind")
	}
	mutators := []func(*WindProbeInput){
		func(p *WindProbeInput) { p.MassKg = 0 },
		func(p *WindProbeInput) { p.StiffnessNPerM = 1e12 },
		func(p *WindProbeInput) { p.DurationS = 100 },
		func(p *WindProbeInput) { p.StepS = 1e-8 },
		func(p *WindProbeInput) { p.WindMeanMPerS = math.NaN() },
		func(p *WindProbeInput) { p.DampingNSPerM = -1 },
		func(p *WindProbeInput) { p.InitialDisplacementM = 3 },
	}
	for i, change := range mutators {
		q := p
		change(&q)
		if _, err := RunWindProbe(q); err == nil {
			t.Fatalf("unbounded case %d admitted", i)
		}
	}
}
func TestWindProbeFailsClosedWhenDisplacementBudgetBreached(t *testing.T) {
	p := SyntheticWindProfile(loadExtendedPreset(t, "triticum_aestivum"))
	p.WindMeanMPerS = 35
	p.GustAmplitudeMPerS = 0
	p.MaxDisplacementM = .00001
	if _, err := RunWindProbe(p); err == nil {
		t.Fatal("extreme wind exceeded cap without failure")
	}
}
