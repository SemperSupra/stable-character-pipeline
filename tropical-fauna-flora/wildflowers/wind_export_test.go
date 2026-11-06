package main

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"math"
	"os"
	"path/filepath"
	"testing"
)

func TestPhysicalWindDriverRejectsTamperedTracesAndClock(t *testing.T) {
	for _, id := range []string{"triticum_aestivum", "zea_mays", "helianthus_annuus", "phyllostachys_aurea", "quercus_robur"} {
		s := loadExtendedPreset(t, id)
		r, err := RunWindProbe(SyntheticWindProfile(s))
		if err != nil {
			t.Fatal(err)
		}
		tr, err := BuildPhysicalWindTrack(s, r)
		if err != nil {
			t.Fatalf("%s: %v", id, err)
		}
		if len(tr.TimesS) != 49 || len(tr.MorphWeights) != 196 || tr.TargetAmplitudeM <= 0 || len(tr.ReceiptSHA256) != 64 {
			t.Fatalf("invalid physical driver %s", id)
		}
		if tr.TimesS[0] != 0 || tr.TimesS[len(tr.TimesS)-1] != s.WindPeriod {
			t.Fatalf("bad clocks %s", id)
		}
		moved := false
		for i := 0; i < len(tr.TimesS); i++ {
			w := tr.MorphWeights[4*i : 4*i+4]
			if w[0] < 0 || w[1] < 0 || w[0] > 1 || w[1] > 1 || w[2] != 0 || w[3] != 0 || w[0]*w[1] != 0 {
				t.Fatalf("invalid weight %s at %d", id, i)
			}
			if w[0]+w[1] > 1e-5 {
				moved = true
			}
		}
		if !moved {
			t.Fatalf("no physical motion at all %s", id)
		}
		corrupted := r
		corrupted.Samples = append([]WindProbeSample(nil), r.Samples...)
		corrupted.Samples[10].TipDisplacementM += .01
		if _, err := BuildPhysicalWindTrack(s, corrupted); err == nil {
			t.Fatalf("tampered trace admitted %s", id)
		}
		corrupted = r
		corrupted.Parameters.MassKg *= 2
		if _, err := BuildPhysicalWindTrack(s, corrupted); err == nil {
			t.Fatalf("changed dynamics admitted %s", id)
		}
		wrong := s
		wrong.ID += "_foreign"
		if _, err := BuildPhysicalWindTrack(wrong, r); err == nil {
			t.Fatal("species mismatch accepted")
		}
		wrong = s
		wrong.WindPeriod = 5
		if _, err := BuildPhysicalWindTrack(wrong, r); err == nil {
			t.Fatal("clock mismatch accepted")
		}
	}
}

func TestActualSerializedPhysicsMorphWeights(t *testing.T) {
	s := loadExtendedPreset(t, "zea_mays")
	receipt, err := RunWindProbe(SyntheticWindProfile(s))
	if err != nil {
		t.Fatal(err)
	}
	track, err := BuildPhysicalWindTrack(s, receipt)
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(t.TempDir(), "maize_physical.glb")
	if err := writeGLBVariant(path, build(s), &receipt); err != nil {
		t.Fatal(err)
	}
	b, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if string(b[:4]) != "glTF" || binary.LittleEndian.Uint32(b[8:12]) != uint32(len(b)) {
		t.Fatal("not a complete GLB")
	}
	jlen := int(binary.LittleEndian.Uint32(b[12:16]))
	var doc struct {
		Meshes []struct {
			Primitives []struct {
				Targets []map[string]int `json:"targets"`
			} `json:"primitives"`
			Extras map[string]any `json:"extras"`
		} `json:"meshes"`
		Animations []struct {
			Name     string                        `json:"name"`
			Extras   map[string]any                `json:"extras"`
			Samplers []struct{ Input, Output int } `json:"samplers"`
			Channels []struct {
				Target struct{ Path string } `json:"target"`
			} `json:"channels"`
		} `json:"animations"`
		Accessors   []struct{ BufferView, Count int }      `json:"accessors"`
		BufferViews []struct{ ByteOffset, ByteLength int } `json:"bufferViews"`
	}
	if err := json.Unmarshal(b[20:20+jlen], &doc); err != nil {
		t.Fatal(err)
	}
	if len(doc.Animations) != 1 || doc.Animations[0].Name != "wind_physics_one_shot" || doc.Animations[0].Channels[0].Target.Path != "weights" || doc.Animations[0].Extras["loop"] != false {
		t.Fatal("physical track mislabeled")
	}
	if doc.Meshes[0].Extras["wind_type"] != "unmeasured-spring-drag-single-lateral-mode" || doc.Meshes[0].Extras["wind_loop_state"] != "not-periodic-and-not-seam-qualified" || doc.Meshes[0].Extras["wind_receipt_sha256"] != track.ReceiptSHA256 {
		t.Fatal("physics qualification/receipt metadata missing")
	}
	for _, p := range doc.Meshes[0].Primitives {
		if len(p.Targets) != 4 {
			t.Fatal("morph targets missing")
		}
	}
	binOff := 20 + jlen + 8
	unpack := func(idx int) []float32 {
		t.Helper()
		ac := doc.Accessors[idx]
		bv := doc.BufferViews[ac.BufferView]
		off := binOff + bv.ByteOffset
		if off < 0 || off+ac.Count*4 > len(b) || bv.ByteLength != ac.Count*4 {
			t.Fatal("bad accessor bounds")
		}
		vals := make([]float32, ac.Count)
		for i := range vals {
			vals[i] = math.Float32frombits(binary.LittleEndian.Uint32(b[off+i*4 : off+(i+1)*4]))
		}
		return vals
	}
	samples := doc.Animations[0].Samplers[0]
	times, weights := unpack(samples.Input), unpack(samples.Output)
	if len(times) != 49 || len(weights) != 196 {
		t.Fatal("actual GLB track size incorrect")
	}
	for i := range times {
		if times[i] != track.TimesS[i] {
			t.Fatalf("decoded time does not match physics %d", i)
		}
	}
	for i := range weights {
		if weights[i] != track.MorphWeights[i] {
			t.Fatalf("decoded animation differs from dynamics %d", i)
		}
	}
	if math.Abs(float64(weights[len(weights)-4])) < 1e-8 {
		t.Fatal("physical driver incorrectly forced seamless endpoint")
	}
}

func TestLegacyMaizeByteContractUnchanged(t *testing.T) {
	s := loadExtendedPreset(t, "zea_mays")
	path := filepath.Join(t.TempDir(), "maize.gLB")
	if err := writeGLB(path, build(s)); err != nil {
		t.Fatal(err)
	}
	b, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	got := sha256.Sum256(b)
	expected := "891bee3894842a4fc1f9f3fa249d52a8fe448810dc8ebe5f3a00b45a651815cc"
	if hex.EncodeToString(got[:]) != expected {
		t.Fatalf("old v0.2 GLB changed: got %x", got)
	}
}
