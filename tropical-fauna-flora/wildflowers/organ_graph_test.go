package main

import (
	"encoding/json"
	"math"
	"os"
	"path/filepath"
	"testing"
)

func TestOrganGraphExactGeometryAndStableParentage(t *testing.T) {
	ids := append([]string{"achillea_millefolium", "centaurea_jacea", "convolvulus_arvensis", "tripleurospermum_inodorum"}, extendedFixtures...)
	for _, id := range ids {
		t.Run(id, func(t *testing.T) {
			s := loadExtendedPreset(t, id)
			a := build(s)
			receipt, err := a.graphReceipt()
			if err != nil {
				t.Fatal(err)
			}
			if !receipt.GeometryVerified || receipt.OrganCount < 2 || receipt.RootCount < 1 || receipt.SHA256 == "" {
				t.Fatalf("incomplete receipt: %+v", receipt)
			}
			second, err := build(s).graphReceipt()
			if err != nil || receipt.SHA256 != second.SHA256 {
				t.Fatalf("nondeterministic organ graph %s: %v", id, err)
			}
			path := filepath.Join(t.TempDir(), "organs.json")
			if err = a.writeOrganReceipt(path); err != nil {
				t.Fatal(err)
			}
			b, err := os.ReadFile(path)
			if err != nil {
				t.Fatal(err)
			}
			var got OrganGraphReceipt
			if err = json.Unmarshal(b, &got); err != nil {
				t.Fatal(err)
			}
			if got.OrganCount != len(a.Organs) || got.SHA256 != receipt.SHA256 {
				t.Fatal("sidecar receipt mismatch")
			}
			for _, o := range a.Organs {
				if math.IsNaN(float64(o.AttachmentM)) || o.Parent >= o.ID {
					t.Fatalf("invalid parent/length %v", o)
				}
			}
		})
	}
}
func TestOrganGraphHostileCorruptionRejects(t *testing.T) {
	s := loadExtendedPreset(t, "zea_mays")
	m := build(s)
	if _, err := m.graphReceipt(); err != nil {
		t.Fatal(err)
	}
	// No false PASS on mesh extent corruption; neither aliasing nor missing coverage.
	m.Organs[0].VertexCount++
	if _, err := m.graphReceipt(); err == nil {
		t.Fatal("overlapping organ extent accepted")
	}
	m = build(s)
	m.Organs[1].Parent = m.Organs[1].ID
	if _, err := m.graphReceipt(); err == nil {
		t.Fatal("cyclic parent accepted")
	}
	m = build(s)
	m.Organs = m.Organs[:len(m.Organs)-1]
	if _, err := m.graphReceipt(); err == nil {
		t.Fatal("missing organ accepted")
	}
}
func TestOrganGraphNoInventedDisconnectedAttachment(t *testing.T) {
	s := loadExtendedPreset(t, "triticum_aestivum")
	m := &Model{G: map[string]*Geo{}, S: s}
	m.leaf(V{2, 2, 2}, V{1, 0, 0}, .3, .02, "leaf")
	r, err := m.graphReceipt()
	if err != nil {
		t.Fatal(err)
	}
	if r.Organs[0].Parent != 0 || r.Organs[0].AttachmentVerified {
		t.Fatal("invented anchor")
	}
}
