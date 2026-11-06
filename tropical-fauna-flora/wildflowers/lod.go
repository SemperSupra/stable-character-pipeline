package main

// Discrete botanical-geometry LOD is separate from development and wind.
// It prunes *whole recorded foliage organs*, never random triangles or
// arbitrary vertices, retaining the stem, flower and fruit source mesh.
// This is a rendering cost proxy, NOT visually qualified vegetation LOD.
import "fmt"

type LODReceipt struct {
	Schema            string `json:"schema"`
	Level             int    `json:"level"`
	Species           string `json:"species"`
	OriginalOrgans    int    `json:"original_organs"`
	RetainedOrgans    int    `json:"retained_organs"`
	OriginalTriangles int    `json:"original_triangles"`
	RetainedTriangles int    `json:"retained_triangles"`
	RemovedFoliage    int    `json:"removed_foliage_organs"`
	Status            string `json:"status"`
}

func totalTriangles(m *Model) int {
	n := 0
	for _, g := range m.G {
		n += len(g.I) / 3
	}
	return n
}

func BuildDiscreteLOD(src *Model, level int) (*Model, LODReceipt, error) {
	r := LODReceipt{Schema: "scp.flora.discrete-organ-lod.v1", Level: level, Status: "illustrative-whole-organ-decimation-not-visual-qa"}
	if src == nil {
		return nil, r, fmt.Errorf("nil LOD model")
	}
	if level < 0 || level > 3 {
		return nil, r, fmt.Errorf("unsupported LOD level")
	}
	if _, err := src.graphReceipt(); err != nil {
		return nil, r, fmt.Errorf("source graph invalid: %w", err)
	}
	r.Species = src.S.ID
	r.OriginalOrgans = len(src.Organs)
	r.OriginalTriangles = totalTriangles(src)
	if level == 0 {
		r.RetainedOrgans = r.OriginalOrgans
		r.RetainedTriangles = r.OriginalTriangles
		return src, r, nil
	}
	stride := 1 << uint(level)
	out := &Model{G: map[string]*Geo{}, S: src.S, LODLevel: level}
	idMap := map[uint32]uint32{}
	oldParents := map[uint32]uint32{}
	leafIndex := 0
	for _, o := range src.Organs {
		if o.Kind == "leaf" {
			shouldKeep := leafIndex%stride == 0
			leafIndex++
			if !shouldKeep {
				r.RemovedFoliage++
				continue
			}
		}
		oldG := src.G[o.Material]
		if oldG == nil {
			return nil, r, fmt.Errorf("LOD missing source material")
		}
		if o.VertexOffset < 0 || o.VertexCount <= 0 || o.VertexOffset+o.VertexCount > len(oldG.P) || o.IndexOffset < 0 || o.IndexCount <= 0 || o.IndexOffset+o.IndexCount > len(oldG.I) {
			return nil, r, fmt.Errorf("LOD invalid organ range")
		}
		newG := out.geo(o.Material)
		po, io := len(newG.P), len(newG.I)
		newG.P = append(newG.P, oldG.P[o.VertexOffset:o.VertexOffset+o.VertexCount]...)
		newG.N = append(newG.N, oldG.N[o.VertexOffset:o.VertexOffset+o.VertexCount]...)
		for _, ix := range oldG.I[o.IndexOffset : o.IndexOffset+o.IndexCount] {
			if ix < uint32(o.VertexOffset) || ix >= uint32(o.VertexOffset+o.VertexCount) {
				return nil, r, fmt.Errorf("LOD cross-organ index")
			}
			newG.I = append(newG.I, uint32(po)+ix-uint32(o.VertexOffset))
		}
		id := uint32(len(out.Organs) + 1)
		no := o
		no.ID = id
		no.VertexOffset = po
		no.IndexOffset = io
		no.Parent = 0
		out.Organs = append(out.Organs, no)
		idMap[o.ID] = id
		oldParents[id] = o.Parent
	}
	for i := range out.Organs {
		o := &out.Organs[i]
		originalParent := oldParents[o.ID]
		for originalParent != 0 {
			if mapped, ok := idMap[originalParent]; ok {
				o.Parent = mapped
				break
			}
			// A nonretained parent must never become an invented verified one.
			o.AttachmentVerified = false
			originalParent = src.Organs[originalParent-1].Parent
		}
		if o.Parent == 0 {
			o.AttachmentVerified = false
			o.AttachmentM = 0
		}
	}
	if _, err := out.graphReceipt(); err != nil {
		return nil, r, fmt.Errorf("LOD output validation: %w", err)
	}
	r.RetainedOrgans = len(out.Organs)
	r.RetainedTriangles = totalTriangles(out)
	if r.RemovedFoliage < 1 || r.RetainedTriangles >= r.OriginalTriangles {
		return nil, r, fmt.Errorf("LOD did not reduce foliage cost")
	}
	return out, r, nil
}
