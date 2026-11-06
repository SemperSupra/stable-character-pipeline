package main

import (
	"fmt"
	"math"
)

func (m *Model) drawBamboo() {
	s, r := m.S, m.R
	for n := 0; n < s.Stems; n++ {
		m.SemanticScope = fmt.Sprintf("drawBamboo/stem/%d", n)
		angle := float64(n) * 2.39996
		base := V{jitter(r, .17), 0, jitter(r, .17)}
		tip := base.add(V{cos(angle) * .10, s.Height * (.74 + .26*r.Float32()), sin(angle) * .10})
		for i := 0; i < s.Internodes; i++ {
			t := float32(i) / float32(s.Internodes)
			u := float32(i+1) / float32(s.Internodes)
			p := base.add(tip.sub(base).mul(t))
			q := base.add(tip.sub(base).mul(u))
			m.tube("stem", []V{p, q}, []float32{.012 * (1 - t*.35), .011 * (1 - u*.35)})
			m.sphere(p, .012*(1-t*.35), "node")
			if i < 2 || i > s.Internodes-2 {
				continue
			}
			a := float64(i)*2.39996 + angle
			branchEnd := q.add(V{cos(a) * .15, .075, sin(a) * .15})
			m.tube("branch", []V{q, branchEnd}, []float32{.004, .001})
			for j := 0; j < 4; j++ {
				aa := a + float64(j)*1.8
				m.leaf(branchEnd, V{cos(aa), .05 + .08*r.Float32(), sin(aa)}, .12+.05*r.Float32(), .013*s.LeafScale, "leaf")
			}
		}
	}
}
func (m *Model) drawShrub() {
	s, r := m.S, m.R
	for n := 0; n < s.Stems; n++ {
		m.SemanticScope = fmt.Sprintf("drawShrub/stem/%d", n)
		theta := 2 * math.Pi * float64(n) / float64(s.Stems)
		root := V{jitter(r, .04), 0, jitter(r, .04)}
		top := root.add(V{cos(theta) * s.CrownRadius * .63, s.Height * (.75 + .25*r.Float32()), sin(theta) * s.CrownRadius * .63})
		m.tube("branch", []V{root, root.add(top.sub(root).mul(.48)), top}, []float32{.019, .012, .006})
		for j := 0; j < s.BranchCount; j++ {
			t := .29 + float32(j)*.55/float32(s.BranchCount)
			m.SemanticScope = fmt.Sprintf("drawShrub/stem/%d/branch/%d", n, j)
			p := root.add(top.sub(root).mul(t))
			a := theta + float64(j)*2.39996
			q := p.add(V{cos(a) * s.CrownRadius * (.38 + .12*r.Float32()), s.Height * (.17 + .10*r.Float32()), sin(a) * s.CrownRadius * (.38 + .12*r.Float32())})
			m.tube("branch", []V{p, q}, []float32{.006, .0015})
			for k := 0; k < 3; k++ {
				b := a + float64(k)*2.1
				u := p.add(q.sub(p).mul(float32(k+1) / 4))
				m.leaf(u, V{cos(b), .26, sin(b)}, .095+.045*r.Float32(), .035*s.LeafScale, "leaf")
			}
			if s.GrowthStage > .68 && j%2 == 0 {
				for b := 0; b < s.FruitCount; b++ {
					aa := float64(b) * 2.39996
					m.sphere(q.add(V{cos(aa) * .025, -.012 * float32(b%3), sin(aa) * .025}), .010, "fruit")
				}
			}
		}
	}
}
func (m *Model) woodyBranch(start, end V, radius float32, depth int, angle float64, needle bool) {
	m.tube("bark", []V{start, start.add(end.sub(start).mul(.54)), end}, []float32{radius, radius * .63, radius * .28})
	s, r := m.S, m.R
	if depth >= s.BranchLevels {
		if needle {
			for j := 0; j < 10; j++ {
				a := angle + float64(j)*2.4
				p := start.add(end.sub(start).mul(float32(j+1) / 11))
				m.leaf(p, V{cos(a), .6, sin(a)}, .12, .006, "leaf")
			}
		} else {
			for j := 0; j < 5; j++ {
				a := angle + float64(j)*2.4
				p := end.add(V{cos(a) * .017, 0, sin(a) * .017})
				m.leaf(p, V{cos(a), .36, sin(a)}, float32(math.Min(float64(s.Height*.025), .20)), .055*s.LeafScale, "leaf")
			}
		}
		return
	}
	// Allometry-like crown approximation; not the Weber-Penn growth equations.
	for j := 0; j < s.BranchCount; j++ {
		t := .35 + .5*float32(j+1)/float32(s.BranchCount+1)
		p := start.add(end.sub(start).mul(t))
		a := angle + float64(j)*2.39996 + float64(jitter(r, .09))
		h := s.Height * float32(math.Pow(.34, float64(depth+1)))
		// Conifers retain an upward-biased whorled branch habit.
		rise := .32
		if needle {
			rise = .22
		}
		q := p.add(V{cos(a) * s.CrownRadius * float32(math.Pow(.51, float64(depth+1))), h*float32(rise) + h*.27*r.Float32(), sin(a) * s.CrownRadius * float32(math.Pow(.51, float64(depth+1)))})
		parentScope := m.SemanticScope
		m.SemanticScope = fmt.Sprintf("%s/child/%d", parentScope, j)
		m.woodyBranch(p, q, radius*.43, depth+1, a, needle)
		m.SemanticScope = parentScope
	}
}
func (m *Model) drawTree(needle bool) {
	s := m.S
	m.SemanticScope = "drawTree/trunk"
	root := V{0, 0, 0}
	trunkEnd := V{0, s.Height * .76, 0}
	m.tube("bark", []V{root, {0, s.Height * .31, 0}, {0, s.Height * .59, 0}, trunkEnd}, []float32{s.StemRadius, s.StemRadius * .77, s.StemRadius * .54, s.StemRadius * .28})
	for tier := 0; tier < s.Internodes; tier++ {
		t := .17 + .74*float32(tier+1)/float32(s.Internodes+1)
		p := V{0, s.Height * t, 0}
		for j := 0; j < s.BranchCount; j++ {
			m.SemanticScope = fmt.Sprintf("drawTree/tier/%d/branch/%d", tier, j)
			a := float64(tier)*1.13 + float64(j)*math.Pi*2/float64(s.BranchCount)
			crown := s.CrownRadius * (1 - .59*t)
			if needle {
				crown = s.CrownRadius * (1 - t)
			}
			q := p.add(V{cos(a) * crown, .04*s.Height + float32(tier)*.008*s.Height, sin(a) * crown})
			m.woodyBranch(p, q, s.StemRadius*.23, 0, a, needle)
		}
	}
	if needle {
		m.SemanticScope = "drawTree/apex"
		tip := V{0, s.Height, 0}
		m.tube("bark", []V{trunkEnd, tip}, []float32{s.StemRadius * .24, .002})
	}
}
