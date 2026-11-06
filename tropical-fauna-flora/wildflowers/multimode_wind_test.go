package main

import (
	"bytes"
	"encoding/binary"
	"encoding/json"
	"math"
	"os"
	"path/filepath"
	"testing"
)

func TestMultiWindModesAndTampering(t *testing.T) {
	for _, id := range []string{"zea_mays", "triticum_aestivum", "helianthus_annuus", "vitis_vinifera", "quercus_robur", "phyllostachys_aurea"} {
		s := loadExtendedPreset(t, id)
		r, err := SyntheticMultiWind(s)
		if err != nil {
			t.Fatalf("%s: %v", id, err)
		}
		a, err := BuildMultiWindTrack(s, r)
		if err != nil {
			t.Fatalf("%s: %v", id, err)
		}
		b, err := BuildMultiWindTrack(s, r)
		if err != nil {
			t.Fatal(err)
		}
		x, _ := json.Marshal(a)
		y, _ := json.Marshal(b)
		if !bytes.Equal(x, y) || len(a.Weights) != 294 || len(a.TimesS) != 49 {
			t.Fatalf("bad deterministic track %s", id)
		}
		nonzero := [3]bool{}
		for i := 0; i < 49; i++ {
			for k := 0; k < 3; k++ {
				p, n := a.Weights[i*6+k*2], a.Weights[i*6+k*2+1]
				if p < 0 || n < 0 || p > 1 || n > 1 || p*n != 0 {
					t.Fatalf("bad complementary weights %s %d %d", id, i, k)
				}
				if p+n > 1e-5 {
					nonzero[k] = true
				}
			}
		}
		for k, v := range nonzero {
			if !v {
				t.Fatalf("motion axis %d absent %s", k, id)
			}
		}
		bad := r
		bad.Leaf.Samples = append([]WindProbeSample(nil), r.Leaf.Samples...)
		bad.Leaf.Samples[5].TipDisplacementM += .005
		if _, err = BuildMultiWindTrack(s, bad); err == nil {
			t.Fatal("tampered leaf accepted")
		}
		bad = r
		bad.Z.Parameters.GustPeriodS += .5
		if _, err = BuildMultiWindTrack(s, bad); err == nil {
			t.Fatal("reprofiled z accepted")
		}
		bad = r
		bad.PlantID += "_swapped"
		if _, err = BuildMultiWindTrack(s, bad); err == nil {
			t.Fatal("swapped species accepted")
		}
	}
}

func TestMultiWindSerializedGLBAndLeafAnchor(t *testing.T) {
	s := loadExtendedPreset(t, "zea_mays")
	r, err := SyntheticMultiWind(s)
	if err != nil {
		t.Fatal(err)
	}
	m := build(s)
	path := filepath.Join(t.TempDir(), "maize.glb")
	if err = writeGLBMulti(path, m, &r); err != nil {
		t.Fatal(err)
	}
	b, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	jlen := int(binary.LittleEndian.Uint32(b[12:16]))
	var doc struct {
		Meshes []struct {
			Primitives []struct {
				Material int
				Targets  []map[string]int
			}
			Weights []float32
			Extras  map[string]any
		}
		Materials  []struct{ Name string }
		Animations []struct {
			Name     string
			Extras   map[string]any
			Samplers []struct{ Input, Output int }
		}
		Accessors   []struct{ BufferView, Count int }
		BufferViews []struct{ ByteOffset, ByteLength int }
	}
	if err = json.Unmarshal(b[20:20+jlen], &doc); err != nil {
		t.Fatal(err)
	}
	if doc.Animations[0].Name != "wind_multimode_one_shot" || doc.Animations[0].Extras["loop"] != false || len(doc.Meshes[0].Weights) != 6 {
		t.Fatal("mislabeled multiwind")
	}
	leafFound := false
	for _, p := range doc.Meshes[0].Primitives {
		if len(p.Targets) != 6 {
			t.Fatal("wrong target count")
		}
		if doc.Materials[p.Material].Name == "leaf" {
			leafFound = true
		}
	}
	if !leafFound {
		t.Fatal("no leaf primitive")
	}
	track, err := BuildMultiWindTrack(s, r)
	if err != nil {
		t.Fatal(err)
	}
	accessor := doc.Accessors[doc.Animations[0].Samplers[0].Output]
	view := doc.BufferViews[accessor.BufferView]
	off := 20 + jlen + 8 + view.ByteOffset
	if accessor.Count != len(track.Weights) || view.ByteLength != 4*len(track.Weights) {
		t.Fatal("bad binary dimensions")
	}
	for i, w := range track.Weights {
		v := math.Float32frombits(binary.LittleEndian.Uint32(b[off+i*4 : off+4*i+4]))
		if v != w {
			t.Fatalf("mismatch at %d", i)
		}
	}
	foliage, err := leafMorphDeltas(m, "leaf", track.Amplitudes[2], 1)
	if err != nil {
		t.Fatal(err)
	}
	moved := false
	for _, d := range foliage {
		if d.Y != 0 {
			moved = true
			break
		}
	}
	if !moved {
		t.Fatal("no leaf flutter geometry")
	}
}
