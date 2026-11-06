package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"math"
	"os"
	"path/filepath"
	"testing"
)

var extendedFixtures = []string{
	"festuca_pratensis", "triticum_aestivum", "avena_sativa", "zea_mays",
	"helianthus_annuus", "vitis_vinifera", "phyllostachys_aurea",
	"corylus_avellana", "quercus_robur", "picea_abies", "secale_cereale", "malus_domestica",
}

func loadExtendedPreset(t *testing.T, name string) Preset {
	t.Helper()
	root := "presets"
	if _, err := os.Stat(root); err != nil {
		root = filepath.Join("..", "presets")
	}
	raw, err := os.ReadFile(filepath.Join(root, name+".json"))
	if err != nil {
		t.Fatal(err)
	}
	var s Preset
	if err = json.Unmarshal(raw, &s); err != nil {
		t.Fatal(err)
	}
	if err = validate(s); err != nil {
		t.Fatalf("%s rejected: %v", name, err)
	}
	return s
}
func TestExtendedFamiliesExportAndDeterminism(t *testing.T) {
	for _, id := range extendedFixtures {
		t.Run(id, func(t *testing.T) {
			s := loadExtendedPreset(t, id)
			a := build(s)
			if len(a.G) < 2 {
				t.Fatalf("%s insufficient organ materials", id)
			}
			n, faces := 0, 0
			for mat, g := range a.G {
				if len(g.P) != len(g.N) || len(g.I)%3 != 0 {
					t.Fatalf("malformed mesh %s", mat)
				}
				for _, p := range g.P {
					if math.IsNaN(float64(p.X)) || math.IsNaN(float64(p.Y)) || math.IsNaN(float64(p.Z)) || math.IsInf(float64(p.Y), 0) {
						t.Fatalf("bad coordinate in %s", mat)
					}
				}
				n += len(g.P)
				faces += len(g.I) / 3
			}
			if n < 100 || n > 175000 || faces < 25 || faces > 80000 {
				t.Fatalf("unbounded geometry: v=%d f=%d", n, faces)
			}
			path1 := filepath.Join(t.TempDir(), "a.glb")
			path2 := filepath.Join(t.TempDir(), "b.glb")
			if err := writeGLB(path1, a); err != nil {
				t.Fatal(err)
			}
			if err := writeGLB(path2, build(s)); err != nil {
				t.Fatal(err)
			}
			b1, _ := os.ReadFile(path1)
			b2, _ := os.ReadFile(path2)
			if !bytes.Equal(b1, b2) {
				t.Fatalf("nondeterministic glb: %x / %x", sha256.Sum256(b1), sha256.Sum256(b2))
			}
			if len(b1) > 16*1024*1024 {
				t.Fatalf("asset too large for POC budget: %d", len(b1))
			}
		})
	}
}
func TestExtendedGrowthAndWindBoundaries(t *testing.T) {
	for _, id := range []string{"triticum_aestivum", "zea_mays", "helianthus_annuus", "vitis_vinifera"} {
		s := loadExtendedPreset(t, id)
		s.GrowthStage = .4
		earlier := build(s)
		s.GrowthStage = .95
		mature := build(s)
		if ge, ok := earlier.G["fruit"]; ok && len(ge.P) != 0 && (id == "zea_mays" || id == "vitis_vinifera") {
			t.Fatalf("premature fruit for %s", id)
		}
		if id == "triticum_aestivum" || id == "zea_mays" || id == "helianthus_annuus" || id == "vitis_vinifera" {
			if len(mature.G) <= len(earlier.G) && id != "vitis_vinifera" {
				t.Fatalf("expected new mature organ for %s", id)
			}
		}
		if math.Abs(float64(sway(V{0, 0, 0}, s.Height, s.WindAmplitude, 0).X)) > 1e-8 {
			t.Fatal("root does not anchor")
		}
	}
}
func TestExtendedInvalids(t *testing.T) {
	s := loadExtendedPreset(t, "quercus_robur")
	bad := []func(*Preset){
		func(q *Preset) { q.Height = 99 }, func(q *Preset) { q.Height = float32(math.NaN()) },
		func(q *Preset) { q.BranchLevels = 7 }, func(q *Preset) { q.BranchCount = 90 },
		func(q *Preset) { q.Internodes = 55 }, func(q *Preset) { q.CrownRadius = -1 },
		func(q *Preset) { q.GrowthStage = 0 }, func(q *Preset) { q.WindAmplitude = float32(math.Inf(1)) },
	}
	for i, m := range bad {
		q := s
		m(&q)
		if err := validate(q); err == nil {
			t.Fatalf("bad param %d accepted", i)
		}
	}
}
