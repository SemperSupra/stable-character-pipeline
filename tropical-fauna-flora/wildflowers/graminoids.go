package main

import (
	"math"
)

// Grasses and cereal crops share internodes, tillers and narrow leaves; their
// inflorescences remain distinct (tuft, wheat spike, oat panicle, maize tassel).
func (m *Model) drawGrass() {
	s, r := m.S, m.R
	for n := 0; n < s.Stems; n++ {
		a := 2*math.Pi*float64(n)/float64(s.Stems) + float64(jitter(r, .18))
		base := V{jitter(r, .045), 0, jitter(r, .045)}
		h := s.Height * (.55 + .45*r.Float32())
		d := V{cos(a) * (.10 + .06*r.Float32()), h, sin(a) * (.10 + .06*r.Float32())}
		m.leaf(base, V{d.X, d.Y, d.Z}, h*.92, .011+.004*r.Float32(), "leaf")
		if n%3 == 0 && s.GrowthStage >= .55 {
			tip := base.add(d)
			m.tube("stem", []V{base, tip}, []float32{.0017, .0004})
			for i := 0; i < 5; i++ {
				t := float32(i+1) / 6
				p := base.add(d.mul(.65 + .35*t))
				off := float64(i) * 2.4
				m.tube("grain", []V{p, p.add(V{cos(off) * .012, .010, sin(off) * .012})}, []float32{.00075, .0002})
			}
		}
	}
}
func (m *Model) drawCereal() {
	s, r := m.S, m.R
	for n := 0; n < s.Stems; n++ {
		a := 2 * math.Pi * float64(n) / float64(s.Stems)
		base := V{jitter(r, .04), 0, jitter(r, .04)}
		tip := base.add(V{cos(a) * .04, s.Height * (.82 + .18*r.Float32()), sin(a) * .04})
		m.tube("stem", []V{base, base.add(tip.sub(base).mul(.5)), tip}, []float32{.0026, .002, .001})
		for j := 0; j < s.LeafPairs; j++ {
			t := float32(j+1) / float32(s.LeafPairs+2)
			p := base.add(tip.sub(base).mul(t))
			side := a + float64(j)*math.Pi
			length := (.18 + .08*r.Float32()) * s.Height
			m.leaf(p, V{cos(side) * .67, .50, sin(side) * .67}, length, .013*s.LeafScale, "leaf")
		}
		if s.GrowthStage < .55 {
			continue
		}
		if s.Template == "oats" {
			// Diffuse, open oat panicle with downward-facing grain-bearing pedicels.
			for j := 0; j < s.EarCount; j++ {
				t := float32(j) / float32(s.EarCount)
				level := tip.add(V{0, .04 + .22*s.Height*t, 0})
				angle := float64(j)*2.39996 + float64(n)
				spread := .08*(1-t) + .018
				end := level.add(V{cos(angle) * spread, -.018, sin(angle) * spread})
				m.tube("stem", []V{level, end}, []float32{.00065, .0003})
				m.sphere(end, .006+(.002*r.Float32()), "grain")
			}
		} else {
			// Dense vertical spike; barley can be another preset using longer awns.
			for j := 0; j < s.EarCount; j++ {
				t := float32(j) / float32(s.EarCount)
				level := tip.add(V{0, s.Height * .17 * t, 0})
				for k := 0; k < 2; k++ {
					a := float64(j)*2.4 + float64(k)*math.Pi
					p := level.add(V{cos(a) * .007, 0, sin(a) * .007})
					m.sphere(p, .006, "grain")
					if s.AwnLength > 0 {
						m.tube("stem", []V{p, p.add(V{cos(a) * s.AwnLength * .18, s.AwnLength, sin(a) * s.AwnLength * .18})}, []float32{.00045, .00005})
					}
				}
			}
		}
	}
}
func (m *Model) drawMaize() {
	s, r := m.S, m.R
	for n := 0; n < s.Stems; n++ {
		base := V{jitter(r, .17), 0, jitter(r, .17)}
		tip := base.add(V{jitter(r, .02), s.Height, jitter(r, .02)})
		m.tube("stem", []V{base, base.add(V{0, s.Height * .25, 0}), base.add(V{0, s.Height * .55, 0}), tip}, []float32{.017, .016, .013, .008})
		for j := 0; j < s.LeafPairs; j++ {
			t := float32(j+1) / float32(s.LeafPairs+2)
			a := 2.4 * float64(j+n)
			p := base.add(tip.sub(base).mul(t))
			// Maize leaves are long, broad and predominantly alternating.
			m.leaf(p, V{cos(a), .13 + .22*r.Float32(), sin(a)}, s.Height*(.29+.14*r.Float32()), .046*s.LeafScale, "leaf")
		}
		if s.GrowthStage < .58 {
			continue
		}
		// Tassel consisting of a main rachis plus several spikelets.
		tassel := tip.add(V{0, .14 * s.Height, 0})
		m.tube("stem", []V{tip, tassel}, []float32{.004, .0006})
		for j := 0; j < 9; j++ {
			a := float64(j) * 2.3999
			src := tip.add(V{0, .022 * s.Height * float32(j%4), 0})
			m.tube("grain", []V{src, src.add(V{cos(a) * s.Height * .06, .10 * s.Height, sin(a) * s.Height * .06})}, []float32{.0017, .0005})
		}
		// Side ear with enclosing husk and short silks, not a harvested naked cob.
		if s.GrowthStage < .70 {
			continue
		}
		cobBase := base.add(V{.04, s.Height * .51, .01})
		cobTip := cobBase.add(V{.045, s.Height * .11, 0})
		m.tube("fruit", []V{cobBase, cobTip}, []float32{.024, .016})
		for k := 0; k < 4; k++ {
			a := float64(k) * math.Pi * .5
			m.leaf(cobBase, V{cos(a) * .45, 1, sin(a) * .45}, s.Height*.14, .026, "leaf")
		}
		for k := 0; k < 5; k++ {
			a := float64(k) * 2.4
			m.tube("flower", []V{cobTip, cobTip.add(V{cos(a) * .012, .025 + s.Height*.03, sin(a) * .012})}, []float32{.0004, .00008})
		}
	}
}
