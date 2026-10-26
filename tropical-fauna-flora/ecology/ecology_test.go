package ecology

import (
	"encoding/json"
	"os"
	"reflect"
	"testing"
)

func fixture(t *testing.T) Scenario {
	t.Helper()
	b, e := os.ReadFile("../examples/earth.json")
	if e != nil {
		t.Fatal(e)
	}
	var s Scenario
	if e = json.Unmarshal(b, &s); e != nil {
		t.Fatal(e)
	}
	return s
}
func TestDeterministicMassConservation(t *testing.T) {
	s := fixture(t)
	a, e := Simulate(s)
	if e != nil {
		t.Fatal(e)
	}
	b, e := Simulate(s)
	if e != nil {
		t.Fatal(e)
	}
	if !reflect.DeepEqual(a, b) || a.DigestSHA256 == "" {
		t.Fatal("non-deterministic result")
	}
	if a.Ledger.InitialG+a.Ledger.RegrowthG-a.Ledger.ConsumedG != a.Ledger.FinalG {
		t.Fatal("mass imbalance")
	}
	if e := TraceIntegrity(a); e != nil {
		t.Fatal(e)
	}
	for _, f := range a.Frames {
		for _, ev := range f.Events {
			if ev.Action == "graze" && ev.BiomassDeltaG > 0 {
				t.Fatalf("positive grazing at tick %d", f.Tick)
			}
		}
	}
}
func TestOrderIndependence(t *testing.T) {
	s := fixture(t)
	a, _ := Simulate(s)
	for l, r := 0, len(s.Patches)-1; l < r; l, r = l+1, r-1 {
		s.Patches[l], s.Patches[r] = s.Patches[r], s.Patches[l]
	}
	for l, r := 0, len(s.Animals)-1; l < r; l, r = l+1, r-1 {
		s.Animals[l], s.Animals[r] = s.Animals[r], s.Animals[l]
	}
	b, e := Simulate(s)
	if e != nil {
		t.Fatal(e)
	}
	if a.DigestSHA256 != b.DigestSHA256 {
		t.Fatal("input ordering changed trace")
	}
}
func TestAlienRuleChangesTrace(t *testing.T) {
	s := fixture(t)
	a, _ := Simulate(s)
	s.LightPermille = 2000
	s.Fidelity = "speculative"
	b, e := Simulate(s)
	if e != nil {
		t.Fatal(e)
	}
	if a.DigestSHA256 == b.DigestSHA256 || a.Ledger.RegrowthG == b.Ledger.RegrowthG {
		t.Fatal("light rule failed to affect growth")
	}
}
func TestRejectInvalidInputs(t *testing.T) {
	bad := []func(*Scenario){
		func(s *Scenario) { s.Ticks = 0 }, func(s *Scenario) { s.LightPermille = -1 },
		func(s *Scenario) { s.Patches[0].BiomassG = -10 }, func(s *Scenario) { s.Patches[0].CapacityG = 1 },
		func(s *Scenario) { s.Patches[0].ID = s.Patches[1].ID },
		func(s *Scenario) { s.Animals[0].Kind = "dragon" },
		func(s *Scenario) { s.Animals[0].Patch = "unknown" },
		func(s *Scenario) { s.Animals[0].IntakeGPerTick = 0 },
		func(s *Scenario) { s.Animals = s.Animals[2:] },
		func(s *Scenario) { s.Animals[2].IntakeGPerTick = 1 },
	}
	for i, mutate := range bad {
		s := fixture(t)
		mutate(&s)
		if _, err := Simulate(s); err == nil {
			t.Fatalf("invalid case %d admitted", i)
		}
	}
}
func TestFollowerTracksGrazingAnimal(t *testing.T) {
	s := fixture(t)
	r, e := Simulate(s)
	if e != nil {
		t.Fatal(e)
	}
	for _, f := range r.Frames {
		byID := map[string]Animal{}
		for _, a := range f.Animals {
			byID[a.ID] = a
		}
		if byID["egret-a"].Patch != byID["buffalo-a"].Patch {
			t.Fatalf("egret-a not attached to buffalo-a tick %d", f.Tick)
		}
		if byID["egret-b"].Patch != byID["buffalo-b"].Patch {
			t.Fatalf("egret-b not attached to buffalo-b tick %d", f.Tick)
		}
	}
}
