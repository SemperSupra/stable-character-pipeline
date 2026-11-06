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

func fixture() Preset {
	return Preset{ID: "test_species", Latin: "Synthetic test specimen", German: "Testpflanze", Template: "mayweed", Seed: 42, Height: .5, Stems: 4, HeadsPerStem: 1, Petals: 14, LeafPairs: 5, FlowerRadius: .035, WindAmplitude: .05, WindPeriod: 4, Colors: map[string][4]float32{"stem": {.2, .3, .1, 1}, "leaf": {.2, .5, .1, 1}, "flower": {1, 1, 1, 1}, "center": {1, .6, .1, 1}}}
}
func TestDeterminismAndVariation(t *testing.T) {
	s := fixture()
	a := build(s)
	b := build(s)
	for n, g := range a.G {
		other := b.G[n]
		if other == nil || len(g.P) != len(other.P) {
			t.Fatalf("nondeterministic size %s", n)
		}
		for i, p := range g.P {
			if p != other.P[i] {
				t.Fatalf("nondeterministic position %s %d", n, i)
			}
		}
	}
	s.Seed++
	c := build(s)
	differ := false
	for name, g := range a.G {
		for i, p := range g.P {
			if i < len(c.G[name].P) && p != c.G[name].P[i] {
				differ = true
				break
			}
		}
	}
	if !differ {
		t.Fatal("seed change failed to change geometry")
	}
}
func TestGLBStructureAndSeam(t *testing.T) {
	s := fixture()
	out := filepath.Join(t.TempDir(), "model.glb")
	if err := writeGLB(out, build(s)); err != nil {
		t.Fatal(err)
	}
	b, err := os.ReadFile(out)
	if err != nil {
		t.Fatal(err)
	}
	if len(b) < 28 || !bytes.Equal(b[:4], []byte("glTF")) || binary.LittleEndian.Uint32(b[4:8]) != 2 || int(binary.LittleEndian.Uint32(b[8:12])) != len(b) {
		t.Fatal("bad GLB header or length")
	}
	jlen := int(binary.LittleEndian.Uint32(b[12:16]))
	if 20+jlen+8 > len(b) || binary.LittleEndian.Uint32(b[16:20]) != 0x4e4f534a {
		t.Fatal("bad GLB JSON chunk")
	}
	var doc struct {
		Meshes []struct {
			Primitives []struct {
				Targets    []map[string]int `json:"targets"`
				Attributes map[string]int   `json:"attributes"`
			} `json:"primitives"`
		} `json:"meshes"`
		Animations []struct {
			Samplers []struct {
				Output int `json:"output"`
			} `json:"samplers"`
			Channels []struct {
				Target struct {
					Path string `json:"path"`
				} `json:"target"`
			} `json:"channels"`
		} `json:"animations"`
		Accessors []struct {
			BufferView int `json:"bufferView"`
			Count      int `json:"count"`
		} `json:"accessors"`
		BufferViews []struct {
			ByteOffset int `json:"byteOffset"`
			ByteLength int `json:"byteLength"`
		} `json:"bufferViews"`
		Buffers []struct {
			ByteLength int `json:"byteLength"`
		} `json:"buffers"`
	}
	if err := json.Unmarshal(b[20:20+jlen], &doc); err != nil {
		t.Fatal(err)
	}
	if len(doc.Animations) != 1 || len(doc.Animations[0].Channels) != 1 || doc.Animations[0].Channels[0].Target.Path != "weights" {
		t.Fatal("missing morph weight animation")
	}
	if len(doc.Meshes) != 1 || len(doc.Meshes[0].Primitives) < 3 {
		t.Fatal("missing named organ materials")
	}
	for _, p := range doc.Meshes[0].Primitives {
		if len(p.Targets) != 4 {
			t.Fatal("target count mismatch")
		}
		if _, ok := p.Attributes["NORMAL"]; !ok {
			t.Fatal("missing normals")
		}
	}
	if doc.Buffers[0].ByteLength <= 0 {
		t.Fatal("missing geometry")
	}
	// Inspect the actual serialized sampler output, not a mathematical surrogate.
	outAccessor := doc.Accessors[doc.Animations[0].Samplers[0].Output]
	outView := doc.BufferViews[outAccessor.BufferView]
	binOffset := 20 + jlen + 8
	first := binOffset + outView.ByteOffset
	if outAccessor.Count != 13*4 || first+outView.ByteLength > len(b) {
		t.Fatal("invalid animation weights buffer bounds")
	}
	for i := 0; i < 4; i++ {
		initial := math.Float32frombits(binary.LittleEndian.Uint32(b[first+i*4 : first+(i+1)*4]))
		lastOff := first + (outAccessor.Count-4+i)*4
		final := math.Float32frombits(binary.LittleEndian.Uint32(b[lastOff : lastOff+4]))
		if initial != 0 || final != 0 {
			t.Fatalf("nonzero seam on weight %d: start %g end %g", i, initial, final)
		}
	}
}
func TestRootAnchoringAndWind(t *testing.T) {
	s := fixture()
	root := V{0, 0, 0}
	top := V{0, s.Height, 0}
	for i := 0; i < 4; i++ {
		if sway(root, s.Height, s.WindAmplitude, i) != root {
			t.Fatal("root vertex moves")
		}
		delta := sway(top, s.Height, s.WindAmplitude, i)
		if math.IsNaN(float64(delta.X)) || math.IsInf(float64(delta.X), 0) {
			t.Fatal("invalid displacement")
		}
		if math.Abs(float64(delta.X)) > float64(s.WindAmplitude)+1e-5 || math.Abs(float64(delta.Z)) > float64(s.WindAmplitude)+1e-5 {
			t.Fatal("unbounded wind")
		}
	}
}
func TestAllPresetsGLB(t *testing.T) {
	for _, tpl := range []string{"yarrow", "knapweed", "bindweed", "mayweed"} {
		s := fixture()
		s.Template = tpl
		s.HeadsPerStem = 5
		model := build(s)
		if len(model.G) == 0 {
			t.Fatalf("empty template %s", tpl)
		}
		for name, g := range model.G {
			if len(g.P) == 0 {
				continue
			}
			for _, p := range g.P {
				if math.IsNaN(float64(p.X)) || math.IsNaN(float64(p.Y)) || math.IsNaN(float64(p.Z)) {
					t.Fatalf("NaN in %s %s", tpl, name)
				}
			}
		}
		if err := writeGLB(filepath.Join(t.TempDir(), tpl+".glb"), model); err != nil {
			t.Fatal(err)
		}
	}
}
func TestBadPresetsRejected(t *testing.T) {
	base := fixture()
	cases := []Preset{}
	a := base
	a.Height = 0
	cases = append(cases, a)
	a = base
	a.Stems = 0
	cases = append(cases, a)
	a = base
	a.Stems = 101
	cases = append(cases, a)
	a = base
	a.WindAmplitude = -1
	cases = append(cases, a)
	a = base
	a.WindAmplitude = 2
	cases = append(cases, a)
	a = base
	a.WindPeriod = 0
	cases = append(cases, a)
	a = base
	a.Template = "fake"
	cases = append(cases, a)
	for i, s := range cases {
		if err := validate(s); err == nil {
			t.Fatalf("invalid case %d accepted", i)
		}
	}
}
