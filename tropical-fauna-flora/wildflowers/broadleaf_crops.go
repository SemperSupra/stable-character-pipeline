package main

import "math"

func (m *Model) drawSunflower() {
	s, r := m.S, m.R
	for n := 0; n < s.Stems; n++ {
		root := V{jitter(r, .13), 0, jitter(r, .13)}
		tip := root.add(V{jitter(r, .04), s.Height * (.9 + .1*r.Float32()), jitter(r, .04)})
		m.tube("stem", []V{root, root.add(tip.sub(root).mul(.55)), tip}, []float32{.017, .014, .008})
		for j := 0; j < s.LeafPairs; j++ {
			t := float32(j+1) / float32(s.LeafPairs+2)
			a := float64(j) * 2.39996
			p := root.add(tip.sub(root).mul(t))
			m.leaf(p, V{cos(a), .3, sin(a)}, s.Height*(.10+.04*r.Float32()), .065*s.LeafScale, "leaf")
		}
		if s.GrowthStage < .58 {
			continue
		}
		// Orient the sunflower head in the X/Y plane, tilted outward in Z,
		// so petal shape is visible from a ground-level camera.
		head := tip.add(V{0, .015, -.01})
		segments := s.Petals * 2
		for j := 0; j < segments; j++ {
			a := 2 * math.Pi * float64(j) / float64(segments)
			b := 2 * math.Pi * float64(j+1) / float64(segments)
			pt := func(rad float32, angle float64) V {
				return head.add(V{rad * cos(angle), rad * sin(angle), -.008 * rad / s.FlowerRadius})
			}
			m.tri("center", head, pt(s.FlowerRadius*.64, a), pt(s.FlowerRadius*.64, b))
		}
		for j := 0; j < s.Petals; j++ {
			a := 2 * math.Pi * float64(j) / float64(s.Petals)
			radial := V{cos(a), sin(a), 0}
			side := V{-sin(a), cos(a), 0}
			shoulder := head.add(radial.mul(s.FlowerRadius * .93))
			tipP := head.add(radial.mul(s.FlowerRadius * 1.5))
			m.tri("flower", head, shoulder.add(side.mul(s.FlowerRadius*.18)), tipP)
			m.tri("flower", head, tipP, shoulder.sub(side.mul(s.FlowerRadius*.18)))
		}
		for j := 0; j < 24; j++ {
			a := float64(j) * 2.39996
			rad := s.FlowerRadius * .59 * float32(math.Sqrt(float64(j+1)/25))
			m.sphere(head.add(V{cos(a) * rad, sin(a) * rad, -.005}), s.FlowerRadius*.045, "grain")
		}
	}
}
func (m *Model) drawGrapevine() {
	s, r := m.S, m.R
	// Train a thick woody trunk into two horizontal cordons, with upward annual canes.
	root := V{0, 0, 0}
	split := V{0, s.Height * .47, 0}
	m.tube("bark", []V{root, {.015, s.Height * .22, 0}, split}, []float32{s.StemRadius, s.StemRadius * .78, s.StemRadius * .52})
	for sign := -1; sign <= 1; sign += 2 {
		end := split.add(V{float32(sign) * s.CrownRadius, 0, 0})
		m.tube("bark", []V{split, end}, []float32{s.StemRadius * .40, s.StemRadius * .15})
		for j := 0; j < s.Internodes; j++ {
			t := float32(j+1) / float32(s.Internodes+1)
			p := split.add(end.sub(split).mul(t))
			q := p.add(V{jitter(r, .04), s.Height * (.25 + .14*r.Float32()), jitter(r, .06)})
			m.tube("stem", []V{p, q}, []float32{.006, .001})
			for k := 0; k < s.LeafPairs; k++ {
				u := p.add(q.sub(p).mul(float32(k+1) / float32(s.LeafPairs+1)))
				a := float64(j*3+k) * 2.39996
				d := V{cos(a), .19, sin(a)}
				m.leaf(u, d, .10+.07*r.Float32(), .058*s.LeafScale, "leaf")
				// Five-lobed silhouette approximation via adjacent auxiliary leaf lobes.
				m.leaf(u, V{cos(a + .48), .23, sin(a + .48)}, .065, .028, "leaf")
				m.leaf(u, V{cos(a - .48), .23, sin(a - .48)}, .065, .028, "leaf")
			}
			if s.GrowthStage < .65 || j%2 != 0 {
				continue
			}
			hang := p.add(V{0, s.Height * .12, 0})
			m.tube("stem", []V{hang, hang.add(V{0, -.11, 0})}, []float32{.0012, .0006})
			for k := 0; k < s.FruitCount; k++ {
				a := float64(k) * 2.39996
				level := float32(k) / float32(s.FruitCount)
				berry := hang.add(V{cos(a) * (.036 * (1 - level*.6)), -.025 - float32(k%5)*.020, sin(a) * (.036 * (1 - level*.6))})
				m.sphere(berry, .013, "fruit")
			}
		}
	}
}
