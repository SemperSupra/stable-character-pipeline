// Tropical Scene v0.1: deterministic procedural GLB/GLTF scene generation.
// No third-party Go dependencies. Coordinate system: X forward, Y lateral, Z up.
package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"math"
	"math/rand"
	"os"
	"path/filepath"
	"sort"
)

type Vec [3]float64
type Mesh struct {
	Name string
	P    []float32
	I    []uint32
	Mat  int
}
type Node struct {
	Name        string    `json:"name"`
	Mesh        *int      `json:"mesh,omitempty"`
	Children    []int     `json:"children,omitempty"`
	Translation []float64 `json:"translation,omitempty"`
	Rotation    []float64 `json:"rotation,omitempty"`
}
type Track struct {
	Node   int
	Path   string
	Times  []float32
	Values []float32
	Width  int
}

// SceneConfig is the shared, deterministic scene contract. Coordinates are meters.
// Adding another species requires a generator adapter; current v0 species are explicit.
type SceneConfig struct {
	Schema           string  `json:"schema"`
	Seed             int64   `json:"seed"`
	DurationSeconds  float64 `json:"duration_seconds"`
	GrassPerMaterial int     `json:"grass_per_material"`
	Buffalo          []Vec   `json:"buffalo"`
	Egrets           []Vec   `json:"egrets"`
	Palms            []Vec   `json:"palms"`
	Bananas          []Vec   `json:"bananas"`
}

func defaultConfig() SceneConfig {
	return SceneConfig{
		Schema: "tropical.scene.v0", Seed: 1337, DurationSeconds: 12, GrassPerMaterial: 340,
		Buffalo: []Vec{{-3.2, -.65, 0}, {-6.9, 1.6, 0}},
		Egrets:  []Vec{{-1, -.95, 0}, {-4.2, -2.95, 0}, {-5.4, 2.75, 0}, {.9, 2.3, 0}},
		Palms:   []Vec{{-8, 5, 0}, {-5, 7, 0}, {2, 7, 0}, {8, 5, 0}, {-10, -5, 0}, {8, -7, 0}},
		Bananas: []Vec{{-8, -4.5, 0}, {-6.7, -5.2, 0}, {-5.3, -5.8, 0}, {5.3, 6, 0}, {6.7, 6.1, 0}},
	}
}
func validateConfig(c SceneConfig) error {
	if c.Schema != "tropical.scene.v0" {
		return fmt.Errorf("unsupported scene schema %q", c.Schema)
	}
	if math.IsNaN(c.DurationSeconds) || math.IsInf(c.DurationSeconds, 0) || c.DurationSeconds < 1 || c.DurationSeconds > 30 {
		return fmt.Errorf("duration_seconds must be 1..30")
	}
	if c.GrassPerMaterial < 0 || c.GrassPerMaterial > 5000 {
		return fmt.Errorf("grass_per_material must be 0..5000")
	}
	if len(c.Buffalo) > 6 || len(c.Egrets) > 20 || len(c.Palms) > 30 || len(c.Bananas) > 30 {
		return fmt.Errorf("entity count exceeds bounded limits")
	}
	for _, list := range [][]Vec{c.Buffalo, c.Egrets, c.Palms, c.Bananas} {
		for _, v := range list {
			for _, x := range v {
				if math.IsNaN(x) || math.IsInf(x, 0) || math.Abs(x) > 100 {
					return fmt.Errorf("entity position not finite or out of range")
				}
			}
		}
	}
	return nil
}

type Builder struct {
	meshes    []Mesh
	nodes     []Node
	tracks    []Track
	materials []map[string]interface{}
	rng       *rand.Rand
	seed      int64
}

func (b *Builder) material(name string, c [3]float64) int {
	n := len(b.materials)
	b.materials = append(b.materials, map[string]interface{}{"name": name, "doubleSided": true, "pbrMetallicRoughness": map[string]interface{}{"baseColorFactor": []float64{c[0], c[1], c[2], 1}, "metallicFactor": 0., "roughnessFactor": .92}})
	return n
}
func (b *Builder) node(name string, mesh int, parent int, t Vec) int {
	n := Node{Name: name, Translation: []float64{t[0], t[1], t[2]}}
	if mesh >= 0 {
		n.Mesh = &mesh
	}
	id := len(b.nodes)
	b.nodes = append(b.nodes, n)
	if parent >= 0 {
		b.nodes[parent].Children = append(b.nodes[parent].Children, id)
	}
	return id
}
func (b *Builder) addMesh(name string, mat int, verts []Vec, faces [][3]uint32) int {
	m := Mesh{Name: name, Mat: mat}
	for _, p := range verts {
		m.P = append(m.P, float32(p[0]), float32(p[1]), float32(p[2]))
	}
	for _, f := range faces {
		m.I = append(m.I, f[:]...)
	}
	id := len(b.meshes)
	b.meshes = append(b.meshes, m)
	return id
}
func makeSphere(center Vec, radii Vec, lat, lon int) ([]Vec, [][3]uint32) {
	v := []Vec{}
	f := [][3]uint32{}
	for i := 0; i <= lat; i++ {
		theta := math.Pi * float64(i) / float64(lat)
		for j := 0; j <= lon; j++ {
			phi := 2 * math.Pi * float64(j) / float64(lon)
			v = append(v, Vec{center[0] + radii[0]*math.Sin(theta)*math.Cos(phi), center[1] + radii[1]*math.Sin(theta)*math.Sin(phi), center[2] + radii[2]*math.Cos(theta)})
		}
	}
	for i := 0; i < lat; i++ {
		for j := 0; j < lon; j++ {
			a := uint32(i*(lon+1) + j)
			q := uint32(lon + 1)
			f = append(f, [3]uint32{a, a + q, a + 1}, [3]uint32{a + 1, a + q, a + q + 1})
		}
	}
	return v, f
}
func makeTube(path []Vec, radii []float64, sides int) ([]Vec, [][3]uint32) {
	v := []Vec{}
	f := [][3]uint32{}
	for i, p := range path {
		var tangent Vec
		if i == 0 {
			tangent = diff(path[1], p)
		} else if i == len(path)-1 {
			tangent = diff(p, path[i-1])
		} else {
			tangent = diff(path[i+1], path[i-1])
		}
		tangent = normalize(tangent)
		u := cross(tangent, Vec{0, 1, 0})
		if length(u) < .05 {
			u = cross(tangent, Vec{1, 0, 0})
		}
		u = normalize(u)
		w := normalize(cross(tangent, u))
		for j := 0; j < sides; j++ {
			a := float64(j) * 2 * math.Pi / float64(sides)
			v = append(v, add(p, scale(add(scale(u, math.Cos(a)), scale(w, math.Sin(a))), radii[i])))
		}
	}
	for i := 0; i < len(path)-1; i++ {
		for j := 0; j < sides; j++ {
			a := uint32(i*sides + j)
			n := uint32(i*sides + (j+1)%sides)
			q := uint32(sides)
			f = append(f, [3]uint32{a, a + q, n}, [3]uint32{n, a + q, n + q})
		}
	}
	return v, f
}
func makeLeaf(lengthV, width float64) ([]Vec, [][3]uint32) {
	v := []Vec{}
	f := [][3]uint32{}
	n := 10
	for i := 0; i <= n; i++ {
		t := float64(i) / float64(n)
		half := width * math.Pow(math.Sin(math.Pi*t), .8)
		z := .12*math.Sin(math.Pi*t) - .13*t*t
		v = append(v, Vec{lengthV * t, -half, z}, Vec{lengthV * t, 0, z + .055*math.Sin(math.Pi*t)}, Vec{lengthV * t, half, z})
	}
	for i := 0; i < n; i++ {
		k := uint32(3 * i)
		f = append(f, [3]uint32{k, k + 3, k + 1}, [3]uint32{k + 1, k + 3, k + 4}, [3]uint32{k + 1, k + 4, k + 2}, [3]uint32{k + 2, k + 4, k + 5})
	}
	return v, f
}
func diff(a, c Vec) Vec          { return Vec{a[0] - c[0], a[1] - c[1], a[2] - c[2]} }
func add(a, c Vec) Vec           { return Vec{a[0] + c[0], a[1] + c[1], a[2] + c[2]} }
func scale(a Vec, k float64) Vec { return Vec{a[0] * k, a[1] * k, a[2] * k} }
func length(a Vec) float64       { return math.Sqrt(a[0]*a[0] + a[1]*a[1] + a[2]*a[2]) }
func normalize(a Vec) Vec        { return scale(a, 1./math.Max(length(a), 1e-12)) }
func cross(a, c Vec) Vec {
	return Vec{a[1]*c[2] - a[2]*c[1], a[2]*c[0] - a[0]*c[2], a[0]*c[1] - a[1]*c[0]}
}
func (b *Builder) sphere(name string, mat, parent int, center, radii Vec) int {
	v, f := makeSphere(center, radii, 9, 12)
	return b.node(name, b.addMesh(name, mat, v, f), parent, Vec{})
}
func (b *Builder) tube(name string, mat, parent int, path []Vec, radii []float64) int {
	v, f := makeTube(path, radii, 7)
	return b.node(name, b.addMesh(name, mat, v, f), parent, Vec{})
}
func (b *Builder) leaf(name string, mat, parent int, at Vec, l, w, angle float64) int {
	v, f := makeLeaf(l, w)
	for i := range v {
		x, y := v[i][0], v[i][1]
		v[i][0] = at[0] + x*math.Cos(angle) - y*math.Sin(angle)
		v[i][1] = at[1] + x*math.Sin(angle) + y*math.Cos(angle)
		v[i][2] += at[2]
	}
	return b.node(name, b.addMesh(name, mat, v, f), parent, Vec{})
}
func quatY(a float64) []float32 {
	return []float32{0, float32(math.Sin(a / 2)), 0, float32(math.Cos(a / 2))}
}
func quatZ(a float64) []float32 {
	return []float32{0, 0, float32(math.Sin(a / 2)), float32(math.Cos(a / 2))}
}
func quatX(a float64) []float32 {
	return []float32{float32(math.Sin(a / 2)), 0, 0, float32(math.Cos(a / 2))}
}
func (b *Builder) animate(id int, path string, width, steps int, duration float64, fn func(float64) []float32) {
	tr := Track{Node: id, Path: path, Width: width}
	for i := 0; i <= steps; i++ {
		t := duration * float64(i) / float64(steps)
		tr.Times = append(tr.Times, float32(t))
		tr.Values = append(tr.Values, fn(t)...)
	}
	b.tracks = append(b.tracks, tr)
}
func (b *Builder) buffalo(id string, at Vec, phase, duration float64, hide, horn, eye, hoof int) {
	root := b.node(id+"/root", -1, -1, at)
	b.sphere(id+"/torso", hide, root, Vec{0, 0, 1.34}, Vec{1.34, .62, .68})
	b.sphere(id+"/shoulder", hide, root, Vec{.65, 0, 1.49}, Vec{.66, .68, .74})
	b.sphere(id+"/hindquarters", hide, root, Vec{-.81, 0, 1.39}, Vec{.55, .58, .65})
	b.sphere(id+"/tail-tuft", hide, root, Vec{-1.34, 0, .73}, Vec{.11, .10, .19})
	b.tube(id+"/tail", hide, root, []Vec{{-1.28, 0, 1.58}, {-1.55, 0, 1.18}, {-1.41, 0, .75}}, []float64{.07, .045, .02})
	head := b.node(id+"/head-pivot", -1, root, Vec{1.02, 0, 1.57})
	b.sphere(id+"/head", hide, head, Vec{.38, 0, -.14}, Vec{.62, .38, .40})
	b.sphere(id+"/muzzle", hide, head, Vec{.83, 0, -.42}, Vec{.36, .34, .24})
	for _, side := range []float64{-1, 1} {
		tag := "L"
		if side > 0 {
			tag = "R"
		}
		b.sphere(id+"/eye-"+tag, eye, head, Vec{.52, side * .337, -.13}, Vec{.065, .045, .065})
		b.sphere(id+"/ear-"+tag, hide, head, Vec{.15, side * .52, .035}, Vec{.20, .27, .095})
		b.tube(id+"/horn-"+tag, horn, head, []Vec{{.1, side * .32, .14}, {.08, side * .57, .27}, {-.04, side * .91, .31}, {-.14, side * 1.12, .45}, {-.06, side * 1.17, .66}}, []float64{.16, .145, .12, .07, .007})
	}
	for i, x := range []float64{-.79, .83} {
		for j, y := range []float64{-.43, .43} {
			leg := b.node(fmt.Sprintf("%s/leg-%d-%d-pivot", id, i, j), -1, root, Vec{x, y, 1.04})
			b.tube(fmt.Sprintf("%s/leg-%d-%d", id, i, j), hide, leg, []Vec{{0, 0, .08}, {.04, 0, -.40}, {.07, 0, -.95}}, []float64{.21, .17, .13})
			b.sphere(fmt.Sprintf("%s/hoof-%d-%d", id, i, j), hoof, leg, Vec{.14, 0, -.96}, Vec{.23, .17, .12})
			p := phase + math.Pi*float64((i+j)%2)
			b.animate(leg, "rotation", 4, 72, duration, func(t float64) []float32 { return quatY(.22 * math.Sin(t*2.3*2*math.Pi+p)) })
		}
	}
	b.animate(head, "rotation", 4, 72, duration, func(t float64) []float32 { g := math.Max(0, math.Sin(t*.57+phase)); return quatY(.17 + .35*g) })
	b.animate(root, "translation", 3, 72, duration, func(t float64) []float32 {
		return []float32{float32(at[0] + .105*t), float32(at[1] + .13*math.Sin(.45*t+phase)), float32(at[2] + .035*math.Abs(math.Sin(t*2.3*math.Pi*2+phase)))}
	})
}
func (b *Builder) egret(id string, at Vec, phase, duration float64, white, beak, legs, eyes int) {
	root := b.node(id+"/root", -1, -1, at)
	b.sphere(id+"/body", white, root, Vec{0, 0, .80}, Vec{.37, .19, .23})
	b.sphere(id+"/wing-left", white, root, Vec{-.07, -.16, .79}, Vec{.33, .09, .12})
	b.sphere(id+"/wing-right", white, root, Vec{-.07, .16, .79}, Vec{.33, .09, .12})
	b.tube(id+"/neck", white, root, []Vec{{.22, 0, .88}, {.27, 0, 1.10}, {.40, 0, 1.27}, {.38, 0, 1.42}}, []float64{.095, .08, .057, .045})
	head := b.node(id+"/head-pivot", -1, root, Vec{.37, 0, 1.41})
	b.sphere(id+"/head", white, head, Vec{.035, 0, 0}, Vec{.135, .105, .12})
	b.tube(id+"/beak", beak, head, []Vec{{.12, 0, -.035}, {.26, 0, -.07}, {.49, 0, -.10}}, []float64{.052, .035, .004})
	for _, side := range []float64{-1, 1} {
		b.sphere(id+"/eye", eyes, head, Vec{.08, side * .087, .03}, Vec{.017, .017, .017})
	}
	for i, y := range []float64{-.095, .095} {
		leg := b.node(fmt.Sprintf("%s/leg-%d", id, i), -1, root, Vec{-.07, y, .60})
		b.tube(fmt.Sprintf("%s/shank-%d", id, i), legs, leg, []Vec{{0, 0, 0}, {.06, 0, -.31}, {.04, 0, -.57}}, []float64{.027, .02, .013})
		b.tube(fmt.Sprintf("%s/toes-%d", id, i), legs, leg, []Vec{{.04, 0, -.57}, {.13, 0, -.58}, {.23, 0, -.57}}, []float64{.025, .018, .007})
		p := phase + float64(i)*math.Pi
		b.animate(leg, "rotation", 4, 60, duration, func(t float64) []float32 { return quatY(.35 * math.Sin(2*math.Pi*t*1.9+p)) })
	}
	b.animate(head, "rotation", 4, 50, duration, func(t float64) []float32 { return quatY(.16 * math.Sin(t*3+phase)) })
	b.animate(root, "translation", 3, 72, duration, func(t float64) []float32 {
		return []float32{float32(at[0] + .14*t), float32(at[1] + .12*math.Sin(.55*t+phase)), float32(at[2])}
	})
}
func (b *Builder) palm(id string, at Vec, duration float64, trunk, frond int) {
	root := b.node(id+"/root", -1, -1, at)
	b.tube(id+"/trunk", trunk, root, []Vec{{0, 0, 0}, {.1, 0, 1.5}, {.27, .08, 3.3}, {.34, .12, 4.7}}, []float64{.21, .16, .12, .09})
	for i := 0; i < 9; i++ {
		a := 2 * math.Pi * float64(i) / 9
		leaf := b.node(fmt.Sprintf("%s/frond-%d", id, i), -1, root, Vec{.34, .12, 4.66})
		v, f := makeLeaf(2.6, .20)
		for j := range v {
			t := v[j][0] / 2.6
			v[j][2] = .19*math.Sin(2*t) - 1.08*t*t
			v[j][0], v[j][1] = v[j][0]*math.Cos(a)-v[j][1]*math.Sin(a), v[j][0]*math.Sin(a)+v[j][1]*math.Cos(a)
		}
		mesh := b.addMesh(id+"/frond-geo", frond, v, f)
		b.nodes[leaf].Mesh = &mesh
		phi := a
		b.animate(leaf, "rotation", 4, 48, duration, func(t float64) []float32 { return quatZ(.028 * math.Sin(1.7*t+phi)) })
	}
}
func (b *Builder) banana(id string, at Vec, duration float64, trunk, leafmat int) {
	root := b.node(id+"/root", -1, -1, at)
	b.tube(id+"/stem", trunk, root, []Vec{{0, 0, 0}, {.02, 0, .7}, {.06, 0, 1.5}, {.08, 0, 2.2}}, []float64{.16, .15, .105, .065})
	for i := 0; i < 7; i++ {
		a := 2 * math.Pi * float64(i) / 7
		h := 2.0 + .14*math.Sin(float64(i))
		leaf := b.node(fmt.Sprintf("%s/leaf-%d", id, i), -1, root, Vec{.05, 0, h})
		v, f := makeLeaf(1.55, .36)
		for j := range v {
			t := v[j][0] / 1.55
			v[j][2] = .42*math.Sin(math.Pi*t*.75) - .45*t*t
			v[j][0], v[j][1] = v[j][0]*math.Cos(a)-v[j][1]*math.Sin(a), v[j][0]*math.Sin(a)+v[j][1]*math.Cos(a)
		}
		mesh := b.addMesh(id+"/leaf-geometry", leafmat, v, f)
		b.nodes[leaf].Mesh = &mesh
		pp := a
		b.animate(leaf, "rotation", 4, 48, duration, func(t float64) []float32 { return quatX(.035 * math.Sin(t*1.8+pp)) })
	}
}
func makeField(cfg SceneConfig) *Builder {
	seed, duration := cfg.Seed, cfg.DurationSeconds
	b := &Builder{rng: rand.New(rand.NewSource(seed)), seed: seed}
	grass := b.material("young-rice-leaves", [3]float64{.29, .54, .12})
	grass2 := b.material("wet-grass", [3]float64{.12, .36, .16})
	grass3 := b.material("sunlit-sedges", [3]float64{.41, .58, .17})
	soil := b.material("wet-field-soil", [3]float64{.29, .24, .17})
	water := b.material("irrigation-water", [3]float64{.16, .43, .45})
	mud := b.material("ditch-bank", [3]float64{.37, .29, .18})
	hide := b.material("buffalo-hide", [3]float64{.24, .21, .20})
	horn := b.material("buffalo-horns", [3]float64{.35, .33, .28})
	eye := b.material("animal-eyes", [3]float64{.025, .027, .03})
	hoof := b.material("buffalo-hooves", [3]float64{.12, .11, .09})
	white := b.material("egret-feathers", [3]float64{.94, .93, .83})
	orange := b.material("egret-beak", [3]float64{.87, .49, .13})
	legmat := b.material("egret-legs", [3]float64{.21, .19, .13})
	palmtrunk := b.material("palm-bark", [3]float64{.43, .32, .20})
	palmleaf := b.material("palm-fronds", [3]float64{.08, .32, .16})
	bananatrunk := b.material("banana-pseudostem", [3]float64{.33, .55, .24})
	bananaleaf := b.material("banana-leaves", [3]float64{.13, .48, .15})
	// Terrain, ditch, and banks are distinct reusable procedural geometry.
	b.terrain("field/ground", soil, -12, 12, -9, 9, -.14)
	b.plane("ditch/water", water, -12, 12, -2.5, -1.2, -.015)
	b.plane("ditch/north-bank", mud, -12, 12, -1.18, -.96, -.08)
	b.plane("ditch/south-bank", mud, -12, 12, -2.75, -2.5, -.08)
	// Grass blades are merged by material to keep the render affordable; seed is stable.
	for group, mat := range []int{grass, grass2, grass3} {
		verts := []Vec{}
		faces := [][3]uint32{}
		for i := 0; i < cfg.GrassPerMaterial; i++ {
			x := -11 + 22*b.rng.Float64()
			y := -8.7 + 17.4*b.rng.Float64()
			if y > -2.65 && y < -1.1 {
				continue
			}
			height := .25 + .42*b.rng.Float64()
			angle := 2 * math.Pi * b.rng.Float64()
			width := .035 + .035*b.rng.Float64()
			base := uint32(len(verts))
			v := []Vec{{x, y, -.12}, {x + math.Cos(angle)*width, y + math.Sin(angle)*width, -.12}, {x + math.Cos(angle)*.18, y + math.Sin(angle)*.18, height}}
			verts = append(verts, v...)
			faces = append(faces, [3]uint32{base, base + 1, base + 2})
		}
		if len(verts) > 0 {
			b.node(fmt.Sprintf("ground/flora/grass-group-%d", group), b.addMesh("grass-tufts", mat, verts, faces), -1, Vec{})
		}
	}
	for i, p := range cfg.Palms {
		b.palm(fmt.Sprintf("flora/palm-%02d", i), p, duration, palmtrunk, palmleaf)
	}
	for i, p := range cfg.Bananas {
		b.banana(fmt.Sprintf("flora/banana-%02d", i), p, duration, bananatrunk, bananaleaf)
	}
	for i, p := range cfg.Buffalo {
		b.buffalo(fmt.Sprintf("fauna/buffalo-%02d", i+1), p, float64(i)*1.5, duration, hide, horn, eye, hoof)
	}
	for i, p := range cfg.Egrets {
		b.egret(fmt.Sprintf("fauna/egret-%02d", i+1), p, float64(i)*1.2, duration, white, orange, legmat, eye)
	}
	return b
}

// glTF 2.0 specifies +Y as the world-up axis; modeling primitives use Z-up.
// One root conversion preserves intuitive model coordinates while exporting compliant GLB.
func (b *Builder) gltfAxisRoot() {
	parents := map[int]bool{}
	for _, n := range b.nodes {
		for _, c := range n.Children {
			parents[c] = true
		}
	}
	roots := []int{}
	for i := range b.nodes {
		if !parents[i] {
			roots = append(roots, i)
		}
	}
	id := b.node("coordinate/z-up-to-gltf-y-up", -1, -1, Vec{})
	b.nodes[id].Children = roots
	b.nodes[id].Rotation = []float64{-math.Sqrt(.5), 0, 0, math.Sqrt(.5)}
}
func (b *Builder) plane(name string, mat int, x0, x1, y0, y1, z float64) {
	v := []Vec{{x0, y0, z}, {x1, y0, z}, {x1, y1, z}, {x0, y1, z}}
	f := [][3]uint32{{0, 1, 2}, {0, 2, 3}}
	b.node(name, b.addMesh(name, mat, v, f), -1, Vec{})
}
func (b *Builder) terrain(name string, mat int, x0, x1, y0, y1, z float64) {
	b.plane(name, mat, x0, x1, y0, y1, z)
}
func align4(b *bytes.Buffer) {
	for b.Len()%4 != 0 {
		b.WriteByte(0)
	}
}
func (b *Builder) gltf() ([]byte, []byte, error) {
	blob := bytes.NewBuffer(nil)
	views := []map[string]interface{}{}
	accessors := []map[string]interface{}{}
	meshJSON := []interface{}{}
	appendFloats := func(v []float32, typ string) int {
		align4(blob)
		offset := blob.Len()
		for _, x := range v {
			_ = binary.Write(blob, binary.LittleEndian, x)
		}
		view := len(views)
		views = append(views, map[string]interface{}{"buffer": 0, "byteOffset": offset, "byteLength": len(v) * 4})
		ac := len(accessors)
		width := 1
		if typ == "VEC3" {
			width = 3
		} else if typ == "VEC4" {
			width = 4
		}
		a := map[string]interface{}{"bufferView": view, "componentType": 5126, "count": len(v) / width, "type": typ}
		if typ == "VEC3" || typ == "SCALAR" {
			minv := make([]float32, width)
			maxv := make([]float32, width)
			if len(v) > 0 {
				copy(minv, v[:width])
				copy(maxv, v[:width])
			}
			for i := 0; i < len(v); i += width {
				for j := 0; j < width; j++ {
					if v[i+j] < minv[j] {
						minv[j] = v[i+j]
					}
					if v[i+j] > maxv[j] {
						maxv[j] = v[i+j]
					}
				}
			}
			a["min"] = minv
			a["max"] = maxv
		}
		accessors = append(accessors, a)
		return ac
	}
	appendIndices := func(v []uint32) int {
		align4(blob)
		offset := blob.Len()
		for _, x := range v {
			_ = binary.Write(blob, binary.LittleEndian, x)
		}
		view := len(views)
		views = append(views, map[string]interface{}{"buffer": 0, "byteOffset": offset, "byteLength": len(v) * 4})
		ac := len(accessors)
		accessors = append(accessors, map[string]interface{}{"bufferView": view, "componentType": 5125, "count": len(v), "type": "SCALAR"})
		return ac
	}
	for _, m := range b.meshes {
		p := appendFloats(m.P, "VEC3")
		i := appendIndices(m.I)
		meshJSON = append(meshJSON, map[string]interface{}{"name": m.Name, "primitives": []interface{}{map[string]interface{}{"attributes": map[string]int{"POSITION": p}, "indices": i, "material": m.Mat}}})
	}
	animSamplers := []interface{}{}
	animChannels := []interface{}{}
	for _, tr := range b.tracks {
		times := appendFloats(tr.Times, "SCALAR")
		typ := "VEC3"
		if tr.Width == 4 {
			typ = "VEC4"
		}
		vals := appendFloats(tr.Values, typ)
		si := len(animSamplers)
		animSamplers = append(animSamplers, map[string]interface{}{"input": times, "output": vals, "interpolation": "LINEAR"})
		animChannels = append(animChannels, map[string]interface{}{"sampler": si, "target": map[string]interface{}{"node": tr.Node, "path": tr.Path}})
	}
	roots := []int{}
	for i := range b.nodes {
		roots = append(roots, i)
	}
	for _, n := range b.nodes {
		for _, kid := range n.Children {
			roots[kid] = -1
		}
	}
	r := []int{}
	for _, id := range roots {
		if id >= 0 {
			r = append(r, id)
		}
	}
	sort.Ints(r)
	doc := map[string]interface{}{"asset": map[string]interface{}{"version": "2.0", "generator": "tropical-scene-go-v0.1"}, "scene": 0, "scenes": []interface{}{map[string]interface{}{"nodes": r}}, "nodes": b.nodes, "meshes": meshJSON, "materials": b.materials, "buffers": []interface{}{map[string]interface{}{"byteLength": blob.Len(), "uri": "tropical_scene.bin"}}, "bufferViews": views, "accessors": accessors, "animations": []interface{}{map[string]interface{}{"name": "Tropical fauna and wind", "samplers": animSamplers, "channels": animChannels}}}
	raw, err := json.MarshalIndent(doc, "", "  ")
	return raw, blob.Bytes(), err
}
func writeGLB(path string, gltf, buf []byte) error {
	var doc map[string]interface{}
	if err := json.Unmarshal(gltf, &doc); err != nil {
		return err
	}
	bs := doc["buffers"].([]interface{})
	delete(bs[0].(map[string]interface{}), "uri")
	j, err := json.Marshal(doc)
	if err != nil {
		return err
	}
	for len(j)%4 != 0 {
		j = append(j, ' ')
	}
	for len(buf)%4 != 0 {
		buf = append(buf, 0)
	}
	total := 12 + 8 + len(j) + 8 + len(buf)
	out := bytes.NewBuffer(nil)
	_ = binary.Write(out, binary.LittleEndian, uint32(0x46546c67))
	_ = binary.Write(out, binary.LittleEndian, uint32(2))
	_ = binary.Write(out, binary.LittleEndian, uint32(total))
	_ = binary.Write(out, binary.LittleEndian, uint32(len(j)))
	_ = binary.Write(out, binary.LittleEndian, uint32(0x4e4f534a))
	out.Write(j)
	_ = binary.Write(out, binary.LittleEndian, uint32(len(buf)))
	_ = binary.Write(out, binary.LittleEndian, uint32(0x004e4942))
	out.Write(buf)
	return os.WriteFile(path, out.Bytes(), 0644)
}
func main() {
	out := flag.String("out", "out", "Output directory")
	configPath := flag.String("config", "", "Optional JSON scene specification")
	seed := flag.Int64("seed", 1337, "Deterministic scene seed")
	duration := flag.Float64("seconds", 12, "Animation seconds")
	flag.Parse()
	if *duration < 1 || *duration > 30 {
		fmt.Fprintln(os.Stderr, "seconds must be 1-30")
		os.Exit(2)
	}
	if err := os.MkdirAll(*out, 0755); err != nil {
		panic(err)
	}
	cfg := defaultConfig()
	cfg.Seed = *seed
	cfg.DurationSeconds = *duration
	if *configPath != "" {
		f, err := os.ReadFile(*configPath)
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(2)
		}
		if len(f) > 1024*1024 {
			fmt.Fprintln(os.Stderr, "Scene config >1 MiB")
			os.Exit(2)
		}
		if err := json.Unmarshal(f, &cfg); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(2)
		}
	}
	if err := validateConfig(cfg); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	b := makeField(cfg)
	b.gltfAxisRoot()
	js, bin, err := b.gltf()
	if err != nil {
		panic(err)
	}
	for name, data := range map[string][]byte{"tropical_scene.gltf": js, "tropical_scene.bin": bin} {
		if err := os.WriteFile(filepath.Join(*out, name), data, 0644); err != nil {
			panic(err)
		}
	}
	if err := writeGLB(filepath.Join(*out, "tropical_scene.glb"), js, bin); err != nil {
		panic(err)
	}
	manifest := map[string]interface{}{"schema": "tropical.scene.receipt.v1", "seed": cfg.Seed, "duration_seconds": cfg.DurationSeconds, "source_scene_config": cfg, "coordinate_system": "internal Z-up meters; glTF Y-up root conversion", "mesh_count": len(b.meshes), "node_count": len(b.nodes), "animation_tracks": len(b.tracks), "materials": len(b.materials), "species": []string{"Bubalus bubalis (provisional low-poly proxy)", "Bubulcus ibis (provisional low-poly proxy)", "Musa sp. banana", "Cocos nucifera palm", "rice/grass field"}, "status": "SYNTHETIC_PROCEDURAL_TECHNICAL_PROTOTYPE", "note": "Geometry and rigid joint motion, not anatomical rigging, botanical fidelity, or validated ecology."}
	hash := sha256.Sum256(js)
	manifest["gltf_json_sha256"] = hex.EncodeToString(hash[:])
	hash = sha256.Sum256(bin)
	manifest["gltf_bin_sha256"] = hex.EncodeToString(hash[:])
	receipt, _ := json.MarshalIndent(manifest, "", "  ")
	_ = os.WriteFile(filepath.Join(*out, "receipt.json"), receipt, 0644)
	fmt.Printf("Wrote procedural scene: %d meshes, %d nodes, %d animation tracks, %d materials\n", len(b.meshes), len(b.nodes), len(b.tracks), len(b.materials))
}
