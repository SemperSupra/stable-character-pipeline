// flora-gen is a deterministic, dependency-free plant prototype generator.
// This proof of concept writes animated glTF 2.0 GLB morph targets for wind.
// It does NOT claim botanical/physical validation or imported third-party meshes.
package main

import (
	"bytes"
	"encoding/binary"
	"encoding/json"
	"flag"
	"fmt"
	"math"
	"math/rand"
	"os"
	"path/filepath"
	"sort"
)

type V struct{ X, Y, Z float32 }

func (a V) add(b V) V       { return V{a.X + b.X, a.Y + b.Y, a.Z + b.Z} }
func (a V) sub(b V) V       { return V{a.X - b.X, a.Y - b.Y, a.Z - b.Z} }
func (a V) mul(k float32) V { return V{a.X * k, a.Y * k, a.Z * k} }
func (a V) norm() V {
	l := float32(math.Sqrt(float64(a.X*a.X + a.Y*a.Y + a.Z*a.Z)))
	if l < 1e-8 {
		return V{0, 1, 0}
	}
	return a.mul(1 / l)
}
func cross(a, b V) V        { return V{a.Y*b.Z - a.Z*b.Y, a.Z*b.X - a.X*b.Z, a.X*b.Y - a.Y*b.X} }
func f(x float64) float32   { return float32(x) }
func sin(x float64) float32 { return f(math.Sin(x)) }
func cos(x float64) float32 { return f(math.Cos(x)) }

// A preset is a descriptive, editable specimen contract, not a taxonomic proof.
type Preset struct {
	ID            string                `json:"id"`
	Latin         string                `json:"latin"`
	German        string                `json:"german"`
	English       string                `json:"english,omitempty"`
	Thai          string                `json:"thai,omitempty"`
	Template      string                `json:"template"`
	Seed          int64                 `json:"seed"`
	Height        float32               `json:"height_m"`
	Stems         int                   `json:"stems"`
	HeadsPerStem  int                   `json:"heads_per_stem"`
	Petals        int                   `json:"petals"`
	LeafPairs     int                   `json:"leaf_pairs"`
	FlowerRadius  float32               `json:"flower_radius_m"`
	WindAmplitude float32               `json:"wind_amplitude_m"`
	WindPeriod    float32               `json:"wind_period_s"`
	Colors        map[string][4]float32 `json:"colors_rgba"`
	CrownRadius   float32               `json:"crown_radius_m"`
	StemRadius    float32               `json:"stem_radius_m"`
	BranchCount   int                   `json:"branch_count"`
	BranchLevels  int                   `json:"branch_levels"`
	Internodes    int                   `json:"internodes"`
	EarCount      int                   `json:"ear_count"`
	FruitCount    int                   `json:"fruit_count"`
	AwnLength     float32               `json:"awn_length_m"`
	LeafScale     float32               `json:"leaf_scale"`
	GrowthStage   float32               `json:"growth_stage"`
}

type Geo struct {
	P []V
	N []V
	I []uint32
}
type Model struct {
	G              map[string]*Geo
	R              *rand.Rand
	S              Preset
	Organs         []Organ
	SemanticScope  string
	SemanticCounts map[string]int
}

func (m *Model) geo(mat string) *Geo {
	if _, ok := m.G[mat]; !ok {
		m.G[mat] = &Geo{}
	}
	return m.G[mat]
}
func (m *Model) tri(mat string, a, b, c V) {
	g := m.geo(mat)
	n := cross(b.sub(a), c.sub(a)).norm()
	o := uint32(len(g.P))
	g.P = append(g.P, a, b, c)
	g.N = append(g.N, n, n, n)
	g.I = append(g.I, o, o+1, o+2)
}
func (m *Model) quad(mat string, a, b, c, d V) { m.tri(mat, a, b, c); m.tri(mat, a, c, d) }
func (m *Model) tube(mat string, points []V, radii []float32) {
	if len(points) < 2 {
		return
	}
	finish := m.recordOrgan("axis", mat, points[0], points)
	defer finish()
	sides := 6
	// tube segments are linked by matching rings; degenerate tips are avoided.
	g := m.geo(mat)
	offset := uint32(len(g.P))
	for i, p := range points {
		tangent := V{0, 1, 0}
		if i == 0 {
			tangent = points[1].sub(points[0]).norm()
		} else if i == len(points)-1 {
			tangent = points[i].sub(points[i-1]).norm()
		} else {
			tangent = points[i+1].sub(points[i-1]).norm()
		}
		aux := V{0, 0, 1}
		if math.Abs(float64(tangent.Z)) > .88 {
			aux = V{1, 0, 0}
		}
		u := cross(tangent, aux).norm()
		v := cross(tangent, u).norm()
		for j := 0; j < sides; j++ {
			a := 2 * math.Pi * float64(j) / float64(sides)
			n := u.mul(cos(a)).add(v.mul(sin(a))).norm()
			g.P = append(g.P, p.add(n.mul(radii[i])))
			g.N = append(g.N, n)
		}
	}
	for i := 0; i < len(points)-1; i++ {
		for j := 0; j < sides; j++ {
			a := offset + uint32(i*sides+j)
			b := offset + uint32(i*sides+(j+1)%sides)
			c := a + uint32(sides)
			d := b + uint32(sides)
			g.I = append(g.I, a, c, b, b, c, d)
		}
	}
}
func (m *Model) disk(center V, radius float32, mat string) {
	finish := m.recordOrgan("disk", mat, center, nil)
	defer finish()
	segments := 8
	for j := 0; j < segments; j++ {
		a := float64(j) * 2 * math.Pi / float64(segments)
		b := float64(j+1) * 2 * math.Pi / float64(segments)
		m.tri(mat, center, center.add(V{radius * cos(a), .001, radius * sin(a)}), center.add(V{radius * cos(b), .001, radius * sin(b)}))
	}
}
func (m *Model) sphere(center V, r float32, mat string) {
	finish := m.recordOrgan("sphere", mat, center, nil)
	defer finish()
	for i := 0; i < 4; i++ {
		a0 := math.Pi * float64(i) / 4
		a1 := math.Pi * float64(i+1) / 4
		for j := 0; j < 8; j++ {
			b0 := float64(j) * math.Pi / 4
			b1 := float64(j+1) * math.Pi / 4
			point := func(a, b float64) V { return center.add(V{r * sin(a) * cos(b), r * cos(a), r * sin(a) * sin(b)}) }
			m.quad(mat, point(a0, b0), point(a0, b1), point(a1, b1), point(a1, b0))
		}
	}
}
func (m *Model) petal(center V, angle float64, length, width float32, mat string, droop float32) {
	finish := m.recordOrgan("petal", mat, center, nil)
	defer finish()
	radial := V{cos(angle), 0, sin(angle)}
	side := V{-sin(angle), 0, cos(angle)}
	tip := center.add(radial.mul(length)).add(V{0, droop, 0})
	shoulder := center.add(radial.mul(length * .55)).add(V{0, droop * .7, 0})
	m.tri(mat, center, shoulder.add(side.mul(width)), tip)
	m.tri(mat, center, tip, shoulder.sub(side.mul(width)))
}
func (m *Model) leaf(base V, direction V, length, width float32, mat string) {
	finish := m.recordOrgan("leaf", mat, base, nil)
	defer finish()
	tangent := direction.norm()
	side := cross(tangent, V{0, 0, 1}).norm()
	if math.Abs(float64(side.Y)) > .7 {
		side = V{0, 0, 1}
	}
	p := base
	for i := 0; i < 5; i++ {
		t0 := float32(i) / 5
		t1 := float32(i+1) / 5
		wid0 := width * sin(math.Pi*float64(t0))
		wid1 := width * sin(math.Pi*float64(t1))
		a := p.add(tangent.mul(length * t0)).add(V{0, .002 * sin(float64(t0)*math.Pi), 0})
		b := p.add(tangent.mul(length * t1)).add(V{0, .002 * sin(float64(t1)*math.Pi), 0})
		m.quad(mat, a.sub(side.mul(wid0)), a.add(side.mul(wid0)), b.add(side.mul(wid1)), b.sub(side.mul(wid1)))
	}
}
func jitter(r *rand.Rand, span float32) float32 { return (r.Float32()*2 - 1) * span }
func (m *Model) stem(root, tip V, radius float32) {
	d := tip.sub(root)
	pts := []V{root, root.add(d.mul(.25)), root.add(d.mul(.55)), root.add(d.mul(.8)), tip}
	rs := []float32{radius, radius * .82, radius * .55, radius * .3, radius * .12}
	m.tube("stem", pts, rs)
}
func (m *Model) drawYarrow() {
	s := m.S
	r := m.R
	for si := 0; si < s.Stems; si++ {
		m.SemanticScope = fmt.Sprintf("drawYarrow/stem/%d", si)
		root := V{jitter(r, .045), 0, jitter(r, .035)}
		tip := V{root.X + jitter(r, .085), s.Height * (.72 + r.Float32()*.28), root.Z + jitter(r, .065)}
		m.stem(root, tip, .0035)
		for i := 1; i <= s.LeafPairs; i++ {
			t := float32(i) / float32(s.LeafPairs+2)
			center := root.add(tip.sub(root).mul(t))
			for side := 0; side < 2; side++ {
				angle := float64(si)*.35 + float64(i)*1.8 + float64(side)*math.Pi
				d := V{cos(angle), .17, sin(angle)}
				length := .025 + .03*r.Float32()
				// Feather-like Yarrow leaves, compounded of a central rachis and narrow leaflets.
				end := center.add(d.mul(length))
				m.tube("stem", []V{center, end}, []float32{.0009, .0002})
				for j := 1; j <= 5; j++ {
					u := float32(j) / 6
					p := center.add(end.sub(center).mul(u))
					a := angle + math.Pi/2
					for sign := -1; sign <= 1; sign += 2 {
						dir := V{cos(a) * float32(sign), .12, sin(a) * float32(sign)}
						m.leaf(p, dir, .007+jitter(r, .002), .0015, "leaf")
					}
				}
			}
		}
		count := s.HeadsPerStem
		for hi := 0; hi < count; hi++ {
			a := 2*math.Pi*float64(hi)/float64(count) + float64(si)*.51
			distance := .015 + .025*r.Float32()
			head := tip.add(V{distance * cos(a), jitter(r, .008), distance * sin(a)})
			m.tube("stem", []V{tip.add(V{0, -.02, 0}), head}, []float32{.0011, .00045})
			for k := 0; k < 9; k++ {
				ang := 2 * math.Pi * float64(k) / 9
				rad := s.FlowerRadius * (.15 + .65*f(float64(k%3)/2))
				c := head.add(V{rad * cos(ang), .0006 * f(float64(k%3)), rad * sin(ang)})
				m.disk(c, .0018, "center")
				for pp := 0; pp < 5; pp++ {
					m.petal(c, 2*math.Pi*float64(pp)/5, .0034, .0014, "flower", .0006)
				}
			}
		}
	}
}
func (m *Model) drawKnapweed() {
	s := m.S
	r := m.R
	for si := 0; si < s.Stems; si++ {
		m.SemanticScope = fmt.Sprintf("drawKnapweed/stem/%d", si)
		root := V{jitter(r, .04), 0, jitter(r, .04)}
		tip := V{root.X + jitter(r, .12), s.Height * (.68 + r.Float32()*.32), root.Z + jitter(r, .1)}
		m.stem(root, tip, .004)
		for j := 1; j <= s.LeafPairs; j++ {
			t := float32(j) / float32(s.LeafPairs+1)
			p := root.add(tip.sub(root).mul(t))
			a := float64(j)*2.4 + float64(si)
			for side := 0; side < 2; side++ {
				dir := V{cos(a + float64(side)*math.Pi), -.06, sin(a + float64(side)*math.Pi)}
				m.leaf(p, dir, .038+.024*r.Float32(), .006, "leaf")
			}
		}
		m.sphere(tip, .011, "bract")
		for k := 0; k < s.Petals; k++ {
			a := 2 * math.Pi * float64(k) / float64(s.Petals)
			h := .011 + .016*r.Float32()
			d := V{cos(a), .9 + .1*r.Float32(), sin(a)}.norm()
			c := tip.add(V{cos(a) * .007, .005, sin(a) * .007})
			end := c.add(d.mul(h))
			m.tube("flower", []V{c, end}, []float32{.0015, .0001})
		}
		m.disk(tip.add(V{0, .009, 0}), .008, "center")
	}
}
func (m *Model) funnel(center V, radius float32) {
	finish := m.recordOrgan("corolla", "flower", center, nil)
	defer finish()
	// Trumpet corolla: attached narrow throat widens to a five-lobed rim.
	rings := 5
	seg := 20
	g := m.geo("flower")
	offset := uint32(len(g.P))
	for i := 0; i <= rings; i++ {
		t := float32(i) / float32(rings)
		rad := radius * (.15 + .85*t*t)
		for j := 0; j < seg; j++ {
			a := 2 * math.Pi * float64(j) / float64(seg)
			scallop := 1 + f(.05*math.Cos(a*5))*t
			p := center.add(V{rad * scallop * cos(a), .010 + t*.035, rad * scallop * sin(a)})
			g.P = append(g.P, p)
			g.N = append(g.N, V{cos(a), .48, sin(a)}.norm())
		}
	}
	for i := 0; i < rings; i++ {
		for j := 0; j < seg; j++ {
			a := offset + uint32(i*seg+j)
			b := offset + uint32(i*seg+(j+1)%seg)
			c := a + uint32(seg)
			d := b + uint32(seg)
			g.I = append(g.I, a, b, c, b, d, c)
		}
	}
	m.disk(center.add(V{0, .013, 0}), radius*.13, "center")
}
func (m *Model) drawBindweed() {
	s := m.S
	r := m.R
	for si := 0; si < s.Stems; si++ {
		m.SemanticScope = fmt.Sprintf("drawBindweed/stem/%d", si)
		a := float64(si) * 2 * math.Pi / float64(s.Stems)
		p0 := V{0, 0, 0}
		p1 := V{cos(a) * s.Height * .42, .055 + jitter(r, .02), sin(a) * s.Height * .42}
		p2 := V{cos(a) * s.Height * .85, .10 + jitter(r, .04), sin(a) * s.Height * .85}
		m.tube("stem", []V{p0, p1, p2}, []float32{.0028, .002, .0007})
		for j := 1; j <= s.LeafPairs; j++ {
			t := float32(j) / float32(s.LeafPairs+1)
			base := p0.add(p2.sub(p0).mul(t))
			ang := a + math.Pi*.5*float64((j%2)*2-1)
			dir := V{cos(ang), .18, sin(ang)}
			m.leaf(base, dir, .035+.025*r.Float32(), .010, "leaf")
			// Arrow-shaped pair of lower lobes.
			m.leaf(base, V{cos(ang + 2.2), .03, sin(ang + 2.2)}, .019, .0045, "leaf")
			m.leaf(base, V{cos(ang - 2.2), .03, sin(ang - 2.2)}, .019, .0045, "leaf")
		}
		m.tube("stem", []V{p2, p2.add(V{0, .013, 0})}, []float32{.0009, .0005})
		m.funnel(p2, s.FlowerRadius)
	}
}
func (m *Model) drawMayweed() {
	s := m.S
	r := m.R
	for si := 0; si < s.Stems; si++ {
		m.SemanticScope = fmt.Sprintf("drawMayweed/stem/%d", si)
		root := V{jitter(r, .025), 0, jitter(r, .025)}
		tip := V{root.X + jitter(r, .075), s.Height * (.65 + r.Float32()*.35), root.Z + jitter(r, .08)}
		m.stem(root, tip, .0025)
		for i := 0; i < s.LeafPairs; i++ {
			p := root.add(tip.sub(root).mul(float32(i+1) / float32(s.LeafPairs+1)))
			a := float64(i)*2.2 + float64(si)
			for side := 0; side < 2; side++ {
				dir := V{cos(a + float64(side)*math.Pi), .15, sin(a + float64(side)*math.Pi)}
				m.leaf(p, dir, .022, .0018, "leaf")
				m.leaf(p.add(V{.002, .006, 0}), dir, .014, .0014, "leaf")
			}
		}
		m.sphere(tip, .008, "center")
		for k := 0; k < s.Petals; k++ {
			m.petal(tip, 2*math.Pi*float64(k)/float64(s.Petals), s.FlowerRadius, .005, "flower", -.005)
		}
	}
}
func build(s Preset) *Model {
	m := &Model{G: map[string]*Geo{}, R: rand.New(rand.NewSource(s.Seed)), S: s}
	switch s.Template {
	case "yarrow":
		m.drawYarrow()
	case "knapweed":
		m.drawKnapweed()
	case "bindweed":
		m.drawBindweed()
	case "mayweed":
		m.drawMayweed()
	case "grass":
		m.drawGrass()
	case "wheat", "oats":
		m.drawCereal()
	case "maize":
		m.drawMaize()
	case "sunflower":
		m.drawSunflower()
	case "grapevine":
		m.drawGrapevine()
	case "bamboo":
		m.drawBamboo()
	case "shrub":
		m.drawShrub()
	case "tree":
		m.drawTree(false)
	case "conifer":
		m.drawTree(true)
	}
	return m
}

type GLB struct {
	Buffer    bytes.Buffer
	Views     []map[string]interface{}
	Accessors []map[string]interface{}
}

func (g *GLB) blob(b []byte, target int) int {
	for g.Buffer.Len()%4 != 0 {
		g.Buffer.WriteByte(0)
	}
	off := g.Buffer.Len()
	g.Buffer.Write(b)
	v := map[string]interface{}{"buffer": 0, "byteOffset": off, "byteLength": len(b)}
	if target > 0 {
		v["target"] = target
	}
	g.Views = append(g.Views, v)
	return len(g.Views) - 1
}
func packV(v []V) []byte {
	out := new(bytes.Buffer)
	for _, p := range v {
		binary.Write(out, binary.LittleEndian, p.X)
		binary.Write(out, binary.LittleEndian, p.Y)
		binary.Write(out, binary.LittleEndian, p.Z)
	}
	return out.Bytes()
}
func packF(v []float32) []byte {
	out := new(bytes.Buffer)
	for _, p := range v {
		binary.Write(out, binary.LittleEndian, p)
	}
	return out.Bytes()
}
func packI(v []uint32) []byte {
	out := new(bytes.Buffer)
	for _, p := range v {
		binary.Write(out, binary.LittleEndian, p)
	}
	return out.Bytes()
}
func (g *GLB) accessor(view, comp, count int, kind string, min, max []float32) int {
	a := map[string]interface{}{"bufferView": view, "componentType": comp, "count": count, "type": kind}
	if len(min) > 0 {
		a["min"] = min
		a["max"] = max
	}
	g.Accessors = append(g.Accessors, a)
	return len(g.Accessors) - 1
}
func (g *GLB) vecAccess(v []V, target bool, bounds bool) int {
	b := g.blob(packV(v), 34962)
	var lo, hi []float32
	if bounds {
		low := V{1e9, 1e9, 1e9}
		high := V{-1e9, -1e9, -1e9}
		for _, p := range v {
			if p.X < low.X {
				low.X = p.X
			}
			if p.Y < low.Y {
				low.Y = p.Y
			}
			if p.Z < low.Z {
				low.Z = p.Z
			}
			if p.X > high.X {
				high.X = p.X
			}
			if p.Y > high.Y {
				high.Y = p.Y
			}
			if p.Z > high.Z {
				high.Z = p.Z
			}
		}
		lo = []float32{low.X, low.Y, low.Z}
		hi = []float32{high.X, high.Y, high.Z}
	}
	_ = target
	return g.accessor(b, 5126, len(v), "VEC3", lo, hi)
}
func (g *GLB) indexAccess(v []uint32) int {
	return g.accessor(g.blob(packI(v), 34963), 5125, len(v), "SCALAR", nil, nil)
}
func sway(p V, height, amp float32, sign int) V {
	h := p.Y / height
	if h < 0 {
		h = 0
	}
	if h > 1.3 {
		h = 1.3
	}
	strength := amp * h * h * (.8 + .2*cos(float64(p.X*11+p.Z*7)))
	switch sign {
	case 0:
		return V{strength, 0, strength * .12}
	case 1:
		return V{-strength, 0, -strength * .12}
	case 2:
		return V{-strength * .1, 0, strength}
	default:
		return V{strength * .1, 0, -strength}
	}
}
func writeGLB(path string, m *Model) error {
	s := m.S
	g := new(GLB)
	mats := []string{}
	for name, geo := range m.G {
		if len(geo.I) > 0 {
			mats = append(mats, name)
		}
	}
	sort.Strings(mats)
	prims := []interface{}{}
	materials := []interface{}{}
	totalVerts, totalFaces := 0, 0
	for mid, name := range mats {
		ge := m.G[name]
		totalVerts += len(ge.P)
		totalFaces += len(ge.I) / 3
		pos := g.vecAccess(ge.P, false, true)
		norm := g.vecAccess(ge.N, false, false)
		idx := g.indexAccess(ge.I)
		targets := []interface{}{}
		for t := 0; t < 4; t++ {
			d := make([]V, len(ge.P))
			for i, p := range ge.P {
				d[i] = sway(p, s.Height, s.WindAmplitude, t)
			}
			targets = append(targets, map[string]interface{}{"POSITION": g.vecAccess(d, true, false)})
		}
		prims = append(prims, map[string]interface{}{"attributes": map[string]interface{}{"POSITION": pos, "NORMAL": norm}, "indices": idx, "material": mid, "mode": 4, "targets": targets})
		color := s.Colors[name]
		if color == [4]float32{} {
			color = [4]float32{.4, .65, .32, 1}
		}
		materials = append(materials, map[string]interface{}{"name": name, "doubleSided": true, "pbrMetallicRoughness": map[string]interface{}{"baseColorFactor": color, "metallicFactor": 0, "roughnessFactor": .93}})
	}
	// Two harmonics in 4 nonnegative morph targets, preserving a seamless 4 s loop.
	const N = 13
	times := make([]float32, N)
	weights := make([]float32, 0, N*4)
	for i := 0; i < N; i++ {
		t := float64(i) / float64(N-1)
		times[i] = float32(t) * s.WindPeriod
		x := math.Sin(t * 2 * math.Pi)
		z := math.Sin(t*4*math.Pi + .0)
		wp, wm, zp, zm := float32(0), float32(0), float32(0), float32(0)
		if x >= 0 {
			wp = f(x)
		} else {
			wm = f(-x)
		}
		if z >= 0 {
			zp = f(z * .55)
		} else {
			zm = f(-z * .55)
		}
		// Exact zero endpoints prevent residual floating-point motion at loop seam.
		if i == 0 || i == N-1 {
			wp, wm, zp, zm = 0, 0, 0, 0
		}
		weights = append(weights, wp, wm, zp, zm)
	}
	ta := g.accessor(g.blob(packF(times), 0), 5126, len(times), "SCALAR", []float32{0}, []float32{s.WindPeriod})
	wa := g.accessor(g.blob(packF(weights), 0), 5126, len(weights), "SCALAR", nil, nil)
	scene := map[string]interface{}{
		"asset": map[string]interface{}{"version": "2.0", "generator": "flora-gen-prototype"},
		"scene": 0, "scenes": []interface{}{map[string]interface{}{"nodes": []int{0}}},
		"nodes":      []interface{}{map[string]interface{}{"name": s.ID, "mesh": 0}},
		"meshes":     []interface{}{map[string]interface{}{"name": s.Latin, "primitives": prims, "weights": []float32{0, 0, 0, 0}, "extras": map[string]interface{}{"species_id": s.ID, "seed": s.Seed, "labels": map[string]string{"la": s.Latin, "en": s.English, "de": s.German, "th": s.Thai}, "parametric_source": "presets/" + s.ID + ".json", "wind_type": "morph-target-approximation", "template": s.Template, "growth_stage_snapshot": s.GrowthStage, "vertices": totalVerts, "triangles": totalFaces}}},
		"materials":  materials,
		"animations": []interface{}{map[string]interface{}{"name": "wind_sway_loop", "samplers": []interface{}{map[string]interface{}{"input": ta, "output": wa, "interpolation": "LINEAR"}}, "channels": []interface{}{map[string]interface{}{"sampler": 0, "target": map[string]interface{}{"node": 0, "path": "weights"}}}}},
		"buffers":    []interface{}{map[string]interface{}{"byteLength": 0}}, "bufferViews": g.Views, "accessors": g.Accessors,
		"extras": map[string]interface{}{"research_prototype": true, "not_botanically_validated": true, "no_third_party_meshes": true},
	}
	raw := g.Buffer.Bytes()
	for len(raw)%4 != 0 {
		raw = append(raw, 0)
	}
	scene["buffers"] = []interface{}{map[string]interface{}{"byteLength": len(raw)}}
	js, err := json.Marshal(scene)
	if err != nil {
		return err
	}
	for len(js)%4 != 0 {
		js = append(js, ' ')
	}
	out := new(bytes.Buffer)
	out.WriteString("glTF")
	binary.Write(out, binary.LittleEndian, uint32(2))
	binary.Write(out, binary.LittleEndian, uint32(12+8+len(js)+8+len(raw)))
	binary.Write(out, binary.LittleEndian, uint32(len(js)))
	binary.Write(out, binary.LittleEndian, uint32(0x4E4F534A))
	out.Write(js)
	binary.Write(out, binary.LittleEndian, uint32(len(raw)))
	binary.Write(out, binary.LittleEndian, uint32(0x004E4942))
	out.Write(raw)
	return os.WriteFile(path, out.Bytes(), 0644)
}
func validate(s Preset) error {
	// Input parsing and geometry budgets are deliberately fail-closed, including NaN/Inf.
	maxH := float32(3)
	if s.Template == "tree" || s.Template == "conifer" {
		maxH = 35
	}
	if s.Template == "bamboo" {
		maxH = 12
	}
	scalars := []float32{s.Height, s.FlowerRadius, s.WindPeriod, s.WindAmplitude, s.CrownRadius, s.StemRadius, s.AwnLength, s.LeafScale, s.GrowthStage}
	for _, v := range scalars {
		if math.IsNaN(float64(v)) || math.IsInf(float64(v), 0) {
			return fmt.Errorf("nonfinite parameter")
		}
	}
	if s.ID == "" || s.Latin == "" || s.Height <= 0 || s.Height > maxH || s.Stems < 1 || s.Stems > 32 || s.HeadsPerStem < 1 || s.HeadsPerStem > 24 || s.Petals < 1 || s.Petals > 64 || s.LeafPairs < 1 || s.LeafPairs > 24 || s.FlowerRadius <= 0 || s.FlowerRadius > .5 || s.WindPeriod <= 0 || s.WindPeriod > 120 || s.WindAmplitude < 0 || s.WindAmplitude > s.Height*.5 {
		return fmt.Errorf("invalid preset scalar or geometry budget")
	}
	switch s.Template {
	case "yarrow", "knapweed", "bindweed", "mayweed":
		return nil
	case "grass", "wheat", "oats", "maize", "sunflower", "grapevine", "bamboo", "shrub", "tree", "conifer":
		if s.BranchCount < 1 || s.BranchCount > 7 || s.BranchLevels < 0 || s.BranchLevels > 3 || s.Internodes < 2 || s.Internodes > 20 || s.EarCount < 1 || s.EarCount > 40 || s.FruitCount < 1 || s.FruitCount > 16 || s.CrownRadius <= 0 || s.CrownRadius > 12 || s.StemRadius <= 0 || s.StemRadius > .8 || s.LeafScale <= 0 || s.LeafScale > 3 || s.GrowthStage <= 0 || s.GrowthStage > 1 || s.AwnLength < 0 || s.AwnLength > .15 {
			return fmt.Errorf("invalid architecture parameter budget")
		}
		return nil
	default:
		return fmt.Errorf("unsupported template %q", s.Template)
	}
}
func run() error {
	input := flag.String("preset", "", "path to species preset json")
	output := flag.String("out", "", "output animated .glb path")
	organs := flag.String("organs", "", "optional geometry-bound organ graph JSON receipt")
	lineage := flag.String("lineage", "", "optional source-path developmental crosswalk JSON")
	windProbe := flag.String("wind-probe", "", "optional synthetic fixed-step reduced-order wind report JSON (not calibrated physical animation)")
	fromStage := flag.Float64("from-stage", .4, "earlier developmental stage for -lineage")
	flag.Parse()
	if *input == "" || *output == "" {
		return fmt.Errorf("usage: flora-gen -preset species.json -out species.glb")
	}
	b, err := os.ReadFile(*input)
	if err != nil {
		return err
	}
	var s Preset
	if err = json.Unmarshal(b, &s); err != nil {
		return err
	}
	if err = validate(s); err != nil {
		return err
	}
	if err = os.MkdirAll(filepath.Dir(*output), 0755); err != nil {
		return err
	}
	m := build(s)
	if *lineage != "" {
		if *fromStage <= 0 || *fromStage >= float64(s.GrowthStage) || math.IsNaN(*fromStage) || math.IsInf(*fromStage, 0) {
			return fmt.Errorf("-from-stage must be finite, positive and strictly less than preset growth_stage")
		}
		earlyPreset := s
		earlyPreset.GrowthStage = float32(*fromStage)
		crosswalk, err := CompareDevelopmentalStages(build(earlyPreset), m)
		if err != nil {
			return err
		}
		if err := os.MkdirAll(filepath.Dir(*lineage), 0755); err != nil {
			return err
		}
		if err := writeDevelopmentalCrosswalk(*lineage, crosswalk); err != nil {
			return err
		}
	}
	if *windProbe != "" {
		probe, e := RunWindProbe(SyntheticWindProfile(s))
		if e != nil {
			return e
		}
		if e = os.MkdirAll(filepath.Dir(*windProbe), 0755); e != nil {
			return e
		}
		if e = writeWindProbe(*windProbe, probe); e != nil {
			return e
		}
	}
	if *organs != "" {
		if err = os.MkdirAll(filepath.Dir(*organs), 0755); err != nil {
			return err
		}
		if err = m.writeOrganReceipt(*organs); err != nil {
			return err
		}
	}
	if err = writeGLB(*output, m); err != nil {
		return err
	}
	v, t := 0, 0
	for _, g := range m.G {
		v += len(g.P)
		t += len(g.I) / 3
	}
	fmt.Printf("%s (%s) -> %s: %d vertices, %d triangles, 4 wind morph targets, %g s loop\n", s.Latin, s.ID, *output, v, t, s.WindPeriod)
	return nil
}
func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
