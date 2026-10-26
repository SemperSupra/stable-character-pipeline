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

func built(t *testing.T, c SceneConfig) ([]byte, []byte, *Builder) {
	t.Helper()
	b := makeField(c)
	b.gltfAxisRoot()
	js, bin, err := b.gltf()
	if err != nil {
		t.Fatal(err)
	}
	return js, bin, b
}
func TestDeterministicAndSeedSensitive(t *testing.T) {
	c := defaultConfig()
	j1, b1, _ := built(t, c)
	j2, b2, _ := built(t, c)
	if !bytes.Equal(j1, j2) || !bytes.Equal(b1, b2) {
		t.Fatal("same config produced different asset bytes")
	}
	c.Seed++
	j3, _, _ := built(t, c)
	if bytes.Equal(j1, j3) {
		t.Fatal("changing seed did not change procedural foliage")
	}
}
func TestSceneConfigValidation(t *testing.T) {
	valid := defaultConfig()
	if err := validateConfig(valid); err != nil {
		t.Fatal(err)
	}
	bad := valid
	bad.Schema = "bad"
	if validateConfig(bad) == nil {
		t.Fatal("invalid schema admitted")
	}
	bad = valid
	bad.DurationSeconds = math.NaN()
	if validateConfig(bad) == nil {
		t.Fatal("NaN duration admitted")
	}
	bad = valid
	bad.GrassPerMaterial = 99999
	if validateConfig(bad) == nil {
		t.Fatal("unbounded foliage admitted")
	}
	bad = valid
	bad.Palms = []Vec{{math.Inf(1), 1, 0}}
	if validateConfig(bad) == nil {
		t.Fatal("nonfinite position admitted")
	}
}
func TestAlternatePopulation(t *testing.T) {
	c := defaultConfig()
	c.Buffalo = c.Buffalo[:1]
	c.Egrets = nil
	c.Palms = nil
	c.Bananas = c.Bananas[:1]
	c.GrassPerMaterial = 0
	if err := validateConfig(c); err != nil {
		t.Fatal(err)
	}
	js, _, b := built(t, c)
	if len(b.meshes) < 10 || len(b.tracks) == 0 {
		t.Fatal("alternate population not generated")
	}
	var doc map[string]interface{}
	if err := json.Unmarshal(js, &doc); err != nil {
		t.Fatal(err)
	}
	names := map[string]bool{}
	for _, raw := range doc["nodes"].([]interface{}) {
		n := raw.(map[string]interface{})
		name := n["name"].(string)
		if names[name] {
			t.Fatalf("duplicate node name: %s", name)
		}
		names[name] = true
	}
	if names["fauna/buffalo-02/root"] {
		t.Fatal("unrequested buffalo generated")
	}
	if names["fauna/egret-01/root"] {
		t.Fatal("unrequested egret generated")
	}
}
func TestGLTFStructureAndAnimation(t *testing.T) {
	js, bin, b := built(t, defaultConfig())
	var obj struct {
		Asset      map[string]interface{}   `json:"asset"`
		Nodes      []map[string]interface{} `json:"nodes"`
		Meshes     []interface{}            `json:"meshes"`
		Animations []struct {
			Channels []struct {
				Target struct {
					Node int    `json:"node"`
					Path string `json:"path"`
				} `json:"target"`
			} `json:"channels"`
		} `json:"animations"`
		Accessors []map[string]interface{} `json:"accessors"`
	}
	if err := json.Unmarshal(js, &obj); err != nil {
		t.Fatal(err)
	}
	if obj.Asset["version"] != "2.0" {
		t.Fatal("wrong GLTF version")
	}
	if len(obj.Meshes) != len(b.meshes) || len(obj.Nodes) != len(b.nodes) {
		t.Fatal("truncated GLTF nodes/meshes")
	}
	if len(obj.Animations) != 1 || len(obj.Animations[0].Channels) != len(b.tracks) {
		t.Fatal("wrong animation count")
	}
	for _, chanl := range obj.Animations[0].Channels {
		if chanl.Target.Node < 0 || chanl.Target.Node >= len(obj.Nodes) {
			t.Fatal("invalid animation target")
		}
		if chanl.Target.Path != "translation" && chanl.Target.Path != "rotation" {
			t.Fatal("unexpected motion path")
		}
	}
	if len(bin) == 0 {
		t.Fatal("empty binary geometry")
	}
	for _, a := range obj.Accessors {
		if a["type"] == "VEC3" && a["min"] == nil {
			t.Fatal("VEC3 bounds omitted")
		}
	}
}
func TestGLBHeader(t *testing.T) {
	js, bin, _ := built(t, defaultConfig())
	f := filepath.Join(t.TempDir(), "test.glb")
	if err := writeGLB(f, js, bin); err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(f)
	if err != nil {
		t.Fatal(err)
	}
	if binary.LittleEndian.Uint32(data[:4]) != 0x46546c67 || binary.LittleEndian.Uint32(data[4:8]) != 2 || int(binary.LittleEndian.Uint32(data[8:12])) != len(data) {
		t.Fatal("invalid GLB header")
	}
	if binary.LittleEndian.Uint32(data[16:20]) != 0x4e4f534a {
		t.Fatal("missing GLB JSON")
	}
}
