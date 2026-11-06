package main

// Geometry-bound organ graph. Each record maps to an exact contiguous range of
// vertices and indices within one material primitive. Attachment inference is
// intentionally provisional and can be replaced with explicit developmental
// parentage as the plant generators mature.
import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math"
	"os"
)

type Organ struct {
	ID                 uint32     `json:"id"`
	Scope              string     `json:"generator_scope"`
	SemanticKey        string     `json:"semantic_key"`
	Parent             uint32     `json:"parent"`
	Kind               string     `json:"kind"`
	Material           string     `json:"material"`
	Anchor             V          `json:"-"`
	AnchorM            [3]float32 `json:"anchor_m"`
	VertexOffset       int        `json:"vertex_offset"`
	VertexCount        int        `json:"vertex_count"`
	IndexOffset        int        `json:"index_offset"`
	IndexCount         int        `json:"index_count"`
	AttachmentM        float32    `json:"attachment_distance_m"`
	AttachmentVerified bool       `json:"attachment_verified"`
	Axis               []V        `json:"-"`
}

type OrganGraphReceipt struct {
	Schema           string  `json:"schema"`
	Species          string  `json:"species"`
	Seed             int64   `json:"seed"`
	Units            string  `json:"units"`
	Status           string  `json:"attachment_status"`
	GrowthStage      float32 `json:"growth_stage"`
	GeometryVerified bool    `json:"geometry_ranges_verified"`
	RootCount        int     `json:"root_attached_count"`
	OrganCount       int     `json:"organ_count"`
	SHA256           string  `json:"organ_records_sha256"`
	Organs           []Organ `json:"organs"`
}

func (m *Model) recordOrgan(kind, material string, anchor V, axis []V) func() {
	geo := m.geo(material)
	p0, i0 := len(geo.P), len(geo.I)
	return func() {
		nP, nI := len(geo.P)-p0, len(geo.I)-i0
		if nP <= 0 || nI <= 0 {
			return
		}
		scope := m.SemanticScope
		if scope == "" {
			scope = "unscoped"
		}
		if m.SemanticCounts == nil {
			m.SemanticCounts = make(map[string]int)
		}
		namespace := fmt.Sprintf("%s/%s/%s", scope, kind, material)
		ordinal := m.SemanticCounts[namespace]
		m.SemanticCounts[namespace] = ordinal + 1
		o := Organ{ID: uint32(len(m.Organs) + 1), Kind: kind, Material: material,
			Scope: scope, SemanticKey: fmt.Sprintf("%s/%d", namespace, ordinal),
			Anchor: anchor, AnchorM: [3]float32{anchor.X, anchor.Y, anchor.Z},
			VertexOffset: p0, VertexCount: nP, IndexOffset: i0, IndexCount: nI}
		if len(axis) > 0 {
			o.Axis = append([]V(nil), axis...)
		}
		if anchor.Y > 0.0001 {
			// Prefer physically connected earlier stem/bark/branch axes.
			// Never invent a parent when no axis lies close enough.
			dist := float32(math.MaxFloat32)
			var parent uint32
			for _, prev := range m.Organs {
				if len(prev.Axis) < 2 {
					continue
				}
				for i := 1; i < len(prev.Axis); i++ {
					d := pointSegmentDistance(anchor, prev.Axis[i-1], prev.Axis[i])
					if d < dist {
						dist, parent = d, prev.ID
					}
				}
			}
			// Tolerance deliberately small: max 1cm or 1% of plant height.
			tolerance := float32(math.Max(.01, float64(m.S.Height)*.01))
			if dist <= tolerance {
				o.Parent = parent
				o.AttachmentM = dist
				o.AttachmentVerified = true
			}
		}
		m.Organs = append(m.Organs, o)
	}
}

func pointSegmentDistance(p, a, b V) float32 {
	d := b.sub(a)
	den := d.X*d.X + d.Y*d.Y + d.Z*d.Z
	if den < 1e-12 {
		v := p.sub(a)
		return float32(math.Sqrt(float64(v.X*v.X + v.Y*v.Y + v.Z*v.Z)))
	}
	v := p.sub(a)
	t := (v.X*d.X + v.Y*d.Y + v.Z*d.Z) / den
	if t < 0 {
		t = 0
	}
	if t > 1 {
		t = 1
	}
	q := a.add(d.mul(t))
	v = p.sub(q)
	return float32(math.Sqrt(float64(v.X*v.X + v.Y*v.Y + v.Z*v.Z)))
}

func (m *Model) graphReceipt() (OrganGraphReceipt, error) {
	rc := OrganGraphReceipt{Schema: "scp.flora.organ-geometry-receipt.v2", Species: m.S.ID, Seed: m.S.Seed, Units: "metre", GrowthStage: m.S.GrowthStage, Status: "heuristic-geometric-parentage-not-developmentally-validated", Organs: m.Organs, OrganCount: len(m.Organs)}
	if len(m.Organs) == 0 {
		return rc, fmt.Errorf("no organ records")
	}
	// Exact coverage of all emitted mesh vertices and indices; no overlaps/gaps.
	cursorP, cursorI := map[string]int{}, map[string]int{}
	semanticKeys := map[string]bool{}
	for j, o := range m.Organs {
		g := m.G[o.Material]
		if g == nil || o.ID != uint32(j+1) || o.Parent >= o.ID || o.VertexCount <= 0 || o.IndexCount <= 0 || o.IndexCount%3 != 0 {
			return rc, fmt.Errorf("invalid organ record %d", j)
		}
		if o.SemanticKey == "" || semanticKeys[o.SemanticKey] {
			return rc, fmt.Errorf("missing/duplicate semantic key at %d", j)
		}
		semanticKeys[o.SemanticKey] = true
		if cursorP[o.Material] != o.VertexOffset || cursorI[o.Material] != o.IndexOffset {
			return rc, fmt.Errorf("organ coverage gap at %d for %s", j, o.Material)
		}
		if o.VertexOffset+o.VertexCount > len(g.P) || o.IndexOffset+o.IndexCount > len(g.I) {
			return rc, fmt.Errorf("organ out of bounds at %d", j)
		}
		cursorP[o.Material] += o.VertexCount
		cursorI[o.Material] += o.IndexCount
		if o.Parent == 0 {
			rc.RootCount++
		}
		if o.AttachmentVerified && (o.Parent == 0 || math.IsNaN(float64(o.AttachmentM)) || o.AttachmentM < 0) {
			return rc, fmt.Errorf("bad attachment %d", j)
		}
	}
	for mat, g := range m.G {
		if cursorP[mat] != len(g.P) || cursorI[mat] != len(g.I) {
			return rc, fmt.Errorf("uncovered geometry for %s", mat)
		}
	}
	b, err := json.Marshal(m.Organs)
	if err != nil {
		return rc, err
	}
	digest := sha256.Sum256(b)
	rc.SHA256 = hex.EncodeToString(digest[:])
	rc.GeometryVerified = true
	return rc, nil
}

func (m *Model) writeOrganReceipt(path string) error {
	receipt, err := m.graphReceipt()
	if err != nil {
		return err
	}
	b, err := json.MarshalIndent(receipt, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(b, '\n'), 0644)
}
