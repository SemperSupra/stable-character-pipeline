package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestDevelopmentalCrosswalkPreservesVegetativeSourcePaths(t *testing.T) {
	candidates := []string{"triticum_aestivum", "avena_sativa", "zea_mays", "helianthus_annuus", "vitis_vinifera", "festuca_pratensis", "corylus_avellana", "quercus_robur", "picea_abies", "phyllostachys_aurea"}
	for _, id := range candidates {
		t.Run(id, func(t *testing.T) {
			s := loadExtendedPreset(t, id)
			s.GrowthStage = .4
			a := build(s)
			s.GrowthStage = .95
			b := build(s)
			x, err := CompareDevelopmentalStages(a, b)
			if err != nil {
				t.Fatalf("%s crosswalk: %v", id, err)
			}
			if len(x.Persistent) < 1 || len(x.Disappeared) != 0 {
				t.Fatalf("%s unexplained source-path loss: %d persistent, %d absent", id, len(x.Persistent), len(x.Disappeared))
			}
			if (id == "zea_mays" || id == "helianthus_annuus" || id == "vitis_vinifera" || id == "triticum_aestivum" || id == "avena_sativa") && len(x.Introduced) == 0 {
				t.Fatal("expected reproductive geometry admission")
			}
			if x.BiologicalIdentityState != "unknown" || x.VisualValidationStatus != "unqualified" {
				t.Fatal("scientific overclaim")
			}
			y, err := CompareDevelopmentalStages(build(func() Preset { q := s; q.GrowthStage = .4; return q }()), build(s))
			if err != nil {
				t.Fatal(err)
			}
			b1, _ := json.Marshal(x)
			b2, _ := json.Marshal(y)
			if !bytes.Equal(b1, b2) {
				t.Fatal("crosswalk nondeterministic")
			}
		})
	}
}
func TestDevelopmentalCrosswalkRejectsIncompatibleInputs(t *testing.T) {
	s := loadExtendedPreset(t, "zea_mays")
	s.GrowthStage = .4
	a := build(s)
	s.GrowthStage = .95
	b := build(s)
	if _, err := CompareDevelopmentalStages(a, b); err != nil {
		t.Fatal(err)
	}
	cases := []struct {
		name string
		f    func(*Preset)
	}{
		{"seed", func(p *Preset) { p.Seed++ }},
		{"species", func(p *Preset) { p.ID = "different" }},
		{"leaf_count", func(p *Preset) { p.LeafPairs++ }},
		{"wind_amplitude", func(p *Preset) { p.WindAmplitude += .002 }},
		{"inverted_stage", func(p *Preset) { p.GrowthStage = .35 }},
	}
	for _, test := range cases {
		t.Run(test.name, func(t *testing.T) {
			q := s
			test.f(&q)
			if _, err := CompareDevelopmentalStages(a, build(q)); err == nil {
				t.Fatal("incompatible DNA admitted")
			}
		})
	}
	if _, err := CompareDevelopmentalStages(nil, b); err == nil {
		t.Fatal("nil model admitted")
	}
	// Graph fabricated without an explicit generator scope cannot claim stable source identity.
	fake := &Model{S: s, G: map[string]*Geo{}}
	fake.leaf(V{0, 0, 0}, V{0, 1, 0}, .1, .01, "leaf")
	q := s
	q.GrowthStage = .95
	other := &Model{S: q, G: map[string]*Geo{}}
	other.leaf(V{0, 0, 0}, V{0, 1, 0}, .1, .01, "leaf")
	if _, err := CompareDevelopmentalStages(fake, other); err == nil {
		t.Fatal("unscoped development claimed")
	}
}
func TestDevelopmentalCrosswalkSidecarAndUnchangedMesh(t *testing.T) {
	s := loadExtendedPreset(t, "helianthus_annuus")
	s.GrowthStage = .95
	m := build(s)
	old := filepath.Join(t.TempDir(), "before.glb")
	newf := filepath.Join(t.TempDir(), "after.glb")
	if err := writeGLB(old, m); err != nil {
		t.Fatal(err)
	}
	early := s
	early.GrowthStage = .4
	x, err := CompareDevelopmentalStages(build(early), m)
	if err != nil {
		t.Fatal(err)
	}
	out := filepath.Join(t.TempDir(), "lineage.json")
	if err := writeDevelopmentalCrosswalk(out, x); err != nil {
		t.Fatal(err)
	}
	bs, err := os.ReadFile(out)
	if err != nil {
		t.Fatal(err)
	}
	var decoded DevelopmentalCrosswalk
	if err := json.Unmarshal(bs, &decoded); err != nil {
		t.Fatal(err)
	}
	if len(decoded.Introduced) == 0 || decoded.ImmutablePresetSHA256 == "" {
		t.Fatal("incomplete lineage receipt")
	}
	if err := writeGLB(newf, m); err != nil {
		t.Fatal(err)
	}
	a, _ := os.ReadFile(old)
	b, _ := os.ReadFile(newf)
	if !bytes.Equal(a, b) {
		t.Fatal("receipt operation changed GLB")
	}
}
