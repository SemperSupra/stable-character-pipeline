package main

import (
	"bytes"
	"crypto/sha256"
	"os"
	"path/filepath"
	"testing"
)

func TestDiscreteLODPreservesSourceAndDeterminism(t *testing.T) {
	for _, id := range []string{"triticum_aestivum", "zea_mays", "phyllostachys_aurea", "quercus_robur", "picea_abies"} {
		s := loadExtendedPreset(t, id)
		m := build(s)
		original := totalTriangles(m)
		var prev = original
		for level := 1; level <= 3; level++ {
			d, r, err := BuildDiscreteLOD(m, level)
			if err != nil {
				t.Fatalf("%s/%d: %v", id, level, err)
			}
			if r.RetainedTriangles >= prev || r.RetainedOrgans >= r.OriginalOrgans || r.RemovedFoliage == 0 {
				t.Fatalf("no meaningful LOD cost decrease %s/%d", id, level)
			}
			prev = r.RetainedTriangles
			for _, o := range d.Organs {
				if o.Parent >= o.ID {
					t.Fatal("orphaned LOD parent")
				}
			}
			if _, err := d.graphReceipt(); err != nil {
				t.Fatal(err)
			}
			file := filepath.Join(t.TempDir(), "lod.glb")
			if err := writeGLB(file, d); err != nil {
				t.Fatal(err)
			}
			b1, err := os.ReadFile(file)
			if err != nil {
				t.Fatal(err)
			}
			d2, _, err := BuildDiscreteLOD(build(s), level)
			if err != nil {
				t.Fatal(err)
			}
			if err := writeGLB(file, d2); err != nil {
				t.Fatal(err)
			}
			b2, err := os.ReadFile(file)
			if err != nil {
				t.Fatal(err)
			}
			if !bytes.Equal(b1, b2) {
				t.Fatalf("LOD nondeterminism %s/%d %x != %x", id, level, sha256.Sum256(b1), sha256.Sum256(b2))
			}
		}
		if totalTriangles(m) != original {
			t.Fatal("source model mutated")
		}
		zeroth, r, err := BuildDiscreteLOD(m, 0)
		if err != nil || zeroth != m || r.RemovedFoliage != 0 {
			t.Fatal("level zero must be identical source")
		}
	}
}
func TestDiscreteLODAdversarial(t *testing.T) {
	s := loadExtendedPreset(t, "zea_mays")
	m := build(s)
	if _, _, err := BuildDiscreteLOD(nil, 1); err == nil {
		t.Fatal("nil model allowed")
	}
	if _, _, err := BuildDiscreteLOD(m, 4); err == nil {
		t.Fatal("unsupported level allowed")
	}
	bad := build(s)
	bad.Organs[0].VertexCount++
	if _, _, err := BuildDiscreteLOD(bad, 1); err == nil {
		t.Fatal("invalid source organ coverage allowed")
	}
	bad = build(s)
	bad.G[bad.Organs[0].Material].I[bad.Organs[0].IndexOffset] = ^uint32(0)
	if _, _, err := BuildDiscreteLOD(bad, 1); err == nil {
		t.Fatal("invalid source index admitted")
	}
}
