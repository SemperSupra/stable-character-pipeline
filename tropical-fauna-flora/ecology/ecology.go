// Package ecology defines an intentionally small, deterministic scene-state
// reference model. This is a behavioral contract fixture, NOT a validated
// biological or biomechanical simulation.
package ecology

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"sort"
)

const Schema = "scp.ecology.v1"

type Scenario struct {
	Schema        string   `json:"schema"`
	Name          string   `json:"name"`
	Fidelity      string   `json:"fidelity"` // earth_prototype | speculative
	Seed          uint64   `json:"seed"`
	Ticks         int      `json:"ticks"`
	LightPermille int64    `json:"light_permille"`
	Patches       []Patch  `json:"patches"`
	Animals       []Animal `json:"animals"`
}
type Patch struct {
	ID               string `json:"id"`
	BiomassG         int64  `json:"biomass_g"`
	CapacityG        int64  `json:"capacity_g"`
	RegrowthGPerTick int64  `json:"regrowth_g_per_tick"`
}
type Animal struct {
	ID             string `json:"id"`
	Kind           string `json:"kind"` // buffalo | egret
	Patch          string `json:"patch"`
	IntakeGPerTick int64  `json:"intake_g_per_tick,omitempty"`
}
type Event struct {
	Tick          int    `json:"tick"`
	Actor         string `json:"actor"`
	Action        string `json:"action"`
	Patch         string `json:"patch"`
	BiomassDeltaG int64  `json:"biomass_delta_g,omitempty"`
}
type Frame struct {
	Tick    int      `json:"tick"`
	Patches []Patch  `json:"patches"`
	Animals []Animal `json:"animals"`
	Events  []Event  `json:"events"`
}
type Ledger struct {
	InitialG  int64 `json:"initial_g"`
	RegrowthG int64 `json:"regrowth_g"`
	ConsumedG int64 `json:"consumed_g"`
	FinalG    int64 `json:"final_g"`
	Balanced  bool  `json:"balanced"`
}
type Report struct {
	Schema       string   `json:"schema"`
	Scenario     string   `json:"scenario"`
	Fidelity     string   `json:"fidelity"`
	Seed         uint64   `json:"seed"`
	Frames       []Frame  `json:"frames"`
	Ledger       Ledger   `json:"ledger"`
	DigestSHA256 string   `json:"digest_sha256"`
	Warnings     []string `json:"warnings"`
}

func (s Scenario) Validate() error {
	if s.Schema != Schema {
		return fmt.Errorf("schema must be %s", Schema)
	}
	if s.Name == "" || len(s.Name) > 96 {
		return errors.New("scenario name required (max 96 chars)")
	}
	if s.Fidelity != "earth_prototype" && s.Fidelity != "speculative" {
		return errors.New("fidelity must be earth_prototype or speculative")
	}
	if s.Ticks < 1 || s.Ticks > 600 {
		return errors.New("ticks must be 1..600")
	}
	if s.LightPermille < 0 || s.LightPermille > 3000 {
		return errors.New("light_permille must be 0..3000")
	}
	if len(s.Patches) == 0 || len(s.Patches) > 128 {
		return errors.New("patch count must be 1..128")
	}
	if len(s.Animals) == 0 || len(s.Animals) > 128 {
		return errors.New("animal count must be 1..128")
	}
	seen := map[string]bool{}
	patchIDs := map[string]bool{}
	for _, p := range s.Patches {
		if p.ID == "" || len(p.ID) > 64 || seen[p.ID] {
			return fmt.Errorf("missing/duplicate/long patch id: %q", p.ID)
		}
		seen[p.ID] = true
		patchIDs[p.ID] = true
		if p.CapacityG <= 0 || p.CapacityG > 1000000000 || p.BiomassG < 0 || p.BiomassG > p.CapacityG || p.RegrowthGPerTick < 0 || p.RegrowthGPerTick > 1000000 {
			return fmt.Errorf("invalid plant biomass/capacity/regrowth: %s", p.ID)
		}
	}
	seen = map[string]bool{}
	buffalo := 0
	for _, a := range s.Animals {
		if a.ID == "" || len(a.ID) > 64 || seen[a.ID] {
			return fmt.Errorf("missing/duplicate/long animal id: %q", a.ID)
		}
		seen[a.ID] = true
		if !patchIDs[a.Patch] {
			return fmt.Errorf("animal %s references missing patch %q", a.ID, a.Patch)
		}
		switch a.Kind {
		case "buffalo":
			buffalo++
			if a.IntakeGPerTick < 1 || a.IntakeGPerTick > 1000000 {
				return fmt.Errorf("bad buffalo intake: %s", a.ID)
			}
		case "egret":
			if a.IntakeGPerTick != 0 {
				return fmt.Errorf("egret %s cannot consume plant biomass", a.ID)
			}
		default:
			return fmt.Errorf("unsupported animal kind: %s", a.Kind)
		}
	}
	if buffalo == 0 {
		return errors.New("at least one buffalo required for tracking behavior")
	}
	return nil
}

func clonePatches(p []Patch) []Patch   { return append([]Patch(nil), p...) }
func cloneAnimals(a []Animal) []Animal { return append([]Animal(nil), a...) }
func sum(p []Patch) int64 {
	var n int64
	for _, x := range p {
		n += x.BiomassG
	}
	return n
}

// Simulate advances plant-resource state and agent attachment relationships.
// Tick = one arbitrary ecology decision interval, not calibrated wall-clock time.
// Regrowth occurs before grazing; sort-by-ID yields order-independent manifests.
func Simulate(s Scenario) (Report, error) {
	if err := s.Validate(); err != nil {
		return Report{}, err
	}
	patches := clonePatches(s.Patches)
	animals := cloneAnimals(s.Animals)
	sort.Slice(patches, func(i, j int) bool { return patches[i].ID < patches[j].ID })
	sort.Slice(animals, func(i, j int) bool { return animals[i].ID < animals[j].ID })
	idx := map[string]int{}
	for i, p := range patches {
		idx[p.ID] = i
	}
	var buffalo []int
	for i, a := range animals {
		if a.Kind == "buffalo" {
			buffalo = append(buffalo, i)
		}
	}
	out := Report{Schema: Schema, Scenario: s.Name, Fidelity: s.Fidelity, Seed: s.Seed,
		Ledger: Ledger{InitialG: sum(patches)}, Warnings: []string{"Synthetic resource and following rules only; no empirical calibration, anatomy, plant growth physiology or contact physics."}}
	for tick := 1; tick <= s.Ticks; tick++ {
		events := make([]Event, 0, len(patches)+len(animals))
		for i := range patches {
			p := &patches[i]
			growth := (p.RegrowthGPerTick * s.LightPermille) / 1000
			if growth > p.CapacityG-p.BiomassG {
				growth = p.CapacityG - p.BiomassG
			}
			if growth > 0 {
				p.BiomassG += growth
				out.Ledger.RegrowthG += growth
				events = append(events, Event{tick, "flora", "regrow", p.ID, growth})
			}
		}
		for n, bi := range buffalo {
			a := &animals[bi]
			// A seeded circular tie-break avoids depending on incoming patch ordering.
			offset := int((s.Seed + uint64(tick) + uint64(n)) % uint64(len(patches)))
			choice := offset
			for k := 1; k < len(patches); k++ {
				j := (offset + k) % len(patches)
				if patches[j].BiomassG > patches[choice].BiomassG {
					choice = j
				}
			}
			p := &patches[choice]
			if a.Patch != p.ID {
				events = append(events, Event{tick, a.ID, "move", p.ID, 0})
				a.Patch = p.ID
			}
			eaten := a.IntakeGPerTick
			if eaten > p.BiomassG {
				eaten = p.BiomassG
			}
			p.BiomassG -= eaten
			out.Ledger.ConsumedG += eaten
			events = append(events, Event{tick, a.ID, "graze", p.ID, -eaten})
		}
		// Egrets follow a buffalo's selected forage patch; no fictitious grass intake.
		e := 0
		for i := range animals {
			if animals[i].Kind != "egret" {
				continue
			}
			leader := animals[buffalo[e%len(buffalo)]]
			e++
			if animals[i].Patch != leader.Patch {
				animals[i].Patch = leader.Patch
				events = append(events, Event{tick, animals[i].ID, "follow", leader.Patch, 0})
			}
		}
		out.Frames = append(out.Frames, Frame{Tick: tick, Patches: clonePatches(patches), Animals: cloneAnimals(animals), Events: events})
	}
	out.Ledger.FinalG = sum(patches)
	out.Ledger.Balanced = out.Ledger.InitialG+out.Ledger.RegrowthG-out.Ledger.ConsumedG == out.Ledger.FinalG
	if !out.Ledger.Balanced {
		return Report{}, errors.New("resource conservation invariant violated")
	}
	canonical, err := json.Marshal(struct {
		Frames []Frame `json:"frames"`
		Ledger Ledger  `json:"ledger"`
	}{out.Frames, out.Ledger})
	if err != nil {
		return Report{}, err
	}
	hash := sha256.Sum256(canonical)
	out.DigestSHA256 = hex.EncodeToString(hash[:])
	return out, nil
}

// TraceIntegrity checks that a report contains matching, nonnegative resource states.
func TraceIntegrity(r Report) error {
	if len(r.Frames) == 0 || !r.Ledger.Balanced {
		return errors.New("missing frames or unbalanced ledger")
	}
	for _, f := range r.Frames {
		for _, p := range f.Patches {
			if p.BiomassG < 0 || p.BiomassG > p.CapacityG {
				return fmt.Errorf("invalid biomass at tick %d", f.Tick)
			}
		}
	}
	return nil
}
