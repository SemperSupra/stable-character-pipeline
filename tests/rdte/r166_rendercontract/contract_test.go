package rendercontract

import (
	"math"
	"slices"
	"strings"
	"testing"
)

func originalFixture() Request {
	h := "sha256:" + strings.Repeat("a", 64)
	return Request{
		Schema: Schema, Frame: Frame,
		Source: SourceBinding{DocumentID: "OriginalDemo", Revision: "revision7", GraphSHA256: h},
		Objects: []Object{
			{ID: "cube", FeaturePath: "root/cube", MaterialID: "blue", Translation: [3]float64{0, 0, 1}, UniformScale: 1},
			{ID: "sphere", FeaturePath: "root/sphere", MaterialID: "red", Translation: [3]float64{2, 0, 1}, UniformScale: 1},
		},
		Materials: []Material{
			{ID: "blue", BaseColor: [3]float64{0.2, 0.3, 0.5}, Roughness: 0.3},
			{ID: "red", BaseColor: [3]float64{0.8, 0.1, 0.1}, Roughness: 0.5},
		},
		Cameras: []Camera{{ID: "maincam", Position: [3]float64{5, -5, 3}, Target: [3]float64{0, 0, 0}, Up: [3]float64{0, 0, 1}, FOVDegrees: 45}},
		Lights:  []Light{{ID: "arealight", Type: "AREA", Position: [3]float64{0, 0, 7}, PowerWatts: 1000, SizeMeters: 5}},
		Options: Options{Engine: Engine, Width: 320, Height: 240, Samples: 32, Seed: 139},
	}
}
func reject(t *testing.T, x Request) {
	t.Helper()
	if _, err := Canonicalize(x); err == nil {
		t.Fatalf("invalid synthetic request accepted: %#v", x)
	}
}
func TestValidOriginalFixture(t *testing.T) {
	if _, err := Canonicalize(originalFixture()); err != nil {
		t.Fatal(err)
	}
}
func TestStableOrderAndCallerOwnership(t *testing.T) {
	x := originalFixture()
	original := slices.Clone(x.Objects)
	a, e := Fingerprint(x)
	if e != nil {
		t.Fatal(e)
	}
	slices.Reverse(x.Objects)
	slices.Reverse(x.Materials)
	b, e := Fingerprint(x)
	if e != nil {
		t.Fatal(e)
	}
	if a != b {
		t.Fatal("declaration order changed fingerprint")
	}
	if x.Objects[0] != original[1] {
		t.Fatal("unexpected input mutation")
	}
	v, e := Canonicalize(x)
	if e != nil {
		t.Fatal(e)
	}
	v.Objects[0].ID = "changed"
	if x.Objects[0].ID == "changed" {
		t.Fatal("returned slice aliases caller")
	}
}
func TestRejectSourceDigest(t *testing.T) {
	for _, bad := range []string{"", "sha256:xyz", "sha256:" + strings.Repeat("g", 64), "sha256:" + strings.Repeat("A", 64)} {
		x := originalFixture()
		x.Source.GraphSHA256 = bad
		reject(t, x)
	}
	x := originalFixture()
	x.Source.InstanceSHA256 = "abc"
	reject(t, x)
}
func TestRejectObjectAndPathCollision(t *testing.T) {
	x := originalFixture()
	x.Objects[1].ID = x.Objects[0].ID
	reject(t, x)
	x = originalFixture()
	x.Objects[1].FeaturePath = x.Objects[0].FeaturePath
	reject(t, x)
}
func TestRejectTraversal(t *testing.T) {
	for _, bad := range []string{"../cube", "root//cube", "/etc/passwd", "root\\cube", "root/../etc", "root/space name"} {
		x := originalFixture()
		x.Objects[0].FeaturePath = bad
		reject(t, x)
	}
}
func TestRejectNonFinite(t *testing.T) {
	for _, v := range []float64{math.NaN(), math.Inf(1), math.Inf(-1)} {
		x := originalFixture()
		x.Materials[0].BaseColor[0] = v
		reject(t, x)
		x = originalFixture()
		x.Objects[0].UniformScale = v
		reject(t, x)
		x = originalFixture()
		x.Lights[0].PowerWatts = v
		reject(t, x)
	}
}
func TestRejectMaterialBoundsAndReferences(t *testing.T) {
	x := originalFixture()
	x.Materials[0].Roughness = 1.1
	reject(t, x)
	x = originalFixture()
	x.Materials[0].BaseColor[0] = -0.1
	reject(t, x)
	x = originalFixture()
	x.Objects[0].MaterialID = "missing"
	reject(t, x)
	x = originalFixture()
	x.Materials[1].ID = x.Materials[0].ID
	reject(t, x)
}
func TestRejectDegenerateAndOverflowCamera(t *testing.T) {
	x := originalFixture()
	x.Cameras[0].Target = x.Cameras[0].Position
	reject(t, x)
	x = originalFixture()
	x.Cameras[0].Up = [3]float64{10, -10, 6}
	reject(t, x)
	x = originalFixture()
	x.Cameras[0].Position = [3]float64{1e308, 0, 0}
	reject(t, x)
	x = originalFixture()
	x.Cameras[0].FOVDegrees = 180
	reject(t, x)
}
func TestRejectLight(t *testing.T) {
	x := originalFixture()
	x.Lights[0].SizeMeters = 0
	reject(t, x)
	x = originalFixture()
	x.Lights[0].Type = "POINT"
	reject(t, x)
	x = originalFixture()
	x.Lights[0].Type = "OTHER"
	reject(t, x)
	x = originalFixture()
	x.Lights = append(x.Lights, x.Lights[0])
	reject(t, x)
}
func TestRejectSamplePixelBudget(t *testing.T) {
	x := originalFixture()
	x.Options.Width = 2048
	x.Options.Height = 2048
	x.Options.Samples = 256
	reject(t, x)
	x = originalFixture()
	x.Options.Samples = 0
	reject(t, x)
}
func TestRejectWrongSchemaFrameOrEngine(t *testing.T) {
	x := originalFixture()
	x.Schema = "v2"
	reject(t, x)
	x = originalFixture()
	x.Frame = "Y_UP"
	reject(t, x)
	x = originalFixture()
	x.Options.Engine = "OTHER"
	reject(t, x)
}
func TestFingerprintChangesWithSourceAndView(t *testing.T) {
	x := originalFixture()
	a, _ := Fingerprint(x)
	x.Cameras[0].Position[0] += 0.2
	b, _ := Fingerprint(x)
	if a == b {
		t.Fatal("camera change omitted")
	}
	x = originalFixture()
	x.Source.Revision = "revision8"
	c, _ := Fingerprint(x)
	if a == c {
		t.Fatal("source change omitted")
	}
}
func TestRejectDeclaredBudgets(t *testing.T) {
	x := originalFixture()
	x.Objects = append(x.Objects, make([]Object, 257)...)
	reject(t, x)
	x = originalFixture()
	x.Cameras = nil
	reject(t, x)
	x = originalFixture()
	x.Lights = nil
	reject(t, x)
}
