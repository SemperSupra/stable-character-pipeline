package main

// A lineage-bound, separate proof about *geometrically inferred* attachments.
// No real botanic parentage is asserted. This flags changed parents, unknown
// attachments and missing source-path dependencies without silencing changes.
import (
	"encoding/json"
	"fmt"
	"os"
	"sort"
)

type AttachmentChange struct {
	SemanticKey   string `json:"semantic_key"`
	EarlierParent string `json:"earlier_parent"`
	LaterParent   string `json:"later_parent"`
	Reason        string `json:"reason"`
}
type ParentageAudit struct {
	Schema                 string             `json:"schema"`
	GeneratorScopeContract string             `json:"generator_scope_contract"`
	Status                 string             `json:"status"`
	Species                string             `json:"species"`
	EarlierStage           float32            `json:"earlier_stage"`
	LaterStage             float32            `json:"later_stage"`
	Persistent             int                `json:"persistent_count"`
	StableGeometricParents int                `json:"stable_geometric_parents"`
	UnresolvedAttachments  int                `json:"unresolved_attachments"`
	ChangedParents         []AttachmentChange `json:"changed_parents"`
	DependencyBreaks       []AttachmentChange `json:"dependency_breaks"`
}

func parentSourceKey(org Organ, all []Organ) (string, error) {
	if org.Parent == 0 {
		return "", nil
	}
	if int(org.Parent) > len(all) || org.Parent >= org.ID {
		return "", fmt.Errorf("parent index invalid")
	}
	p := all[org.Parent-1]
	if p.SemanticKey == "" {
		return "", fmt.Errorf("parent lacks authored semantic key")
	}
	return p.SemanticKey, nil
}
func AuditGeometricParentCorrespondence(early, late *Model) (ParentageAudit, error) {
	out := ParentageAudit{Schema: "scp.flora.geometric-parent-correspondence.v1", GeneratorScopeContract: FloraSemanticScopeContract, Status: "heuristic-geometric-parentage-not-botanical-lineage", ChangedParents: []AttachmentChange{}, DependencyBreaks: []AttachmentChange{}}
	cross, err := CompareDevelopmentalStages(early, late)
	if err != nil {
		return out, err
	}
	a, err := early.graphReceipt()
	if err != nil {
		return out, err
	}
	b, err := late.graphReceipt()
	if err != nil {
		return out, err
	}
	out.Species = cross.Species
	out.EarlierStage = cross.EarlierStage
	out.LaterStage = cross.LaterStage
	out.Persistent = len(cross.Persistent)
	em := map[string]Organ{}
	lm := map[string]Organ{}
	for _, o := range a.Organs {
		em[o.SemanticKey] = o
	}
	for _, o := range b.Organs {
		lm[o.SemanticKey] = o
	}
	for _, e := range cross.Persistent {
		ao, bo := em[e.Key], lm[e.Key]
		ap, err := parentSourceKey(ao, a.Organs)
		if err != nil {
			return out, err
		}
		bp, err := parentSourceKey(bo, b.Organs)
		if err != nil {
			return out, err
		}
		if !ao.AttachmentVerified || !bo.AttachmentVerified {
			out.UnresolvedAttachments++
			continue
		}
		if ap != bp {
			out.ChangedParents = append(out.ChangedParents, AttachmentChange{SemanticKey: e.Key, EarlierParent: ap, LaterParent: bp, Reason: "geometric-nearest-axis-parent-drift"})
		} else {
			out.StableGeometricParents++
		}
		if ap != "" {
			if _, exists := lm[ap]; !exists {
				out.DependencyBreaks = append(out.DependencyBreaks, AttachmentChange{SemanticKey: e.Key, EarlierParent: ap, LaterParent: bp, Reason: "previously-referenced-parent-source-path-not-in-later-graph"})
			}
		}
	}
	cmp := func(x []AttachmentChange) {
		sort.Slice(x, func(i, j int) bool { return x[i].SemanticKey < x[j].SemanticKey })
	}
	cmp(out.ChangedParents)
	cmp(out.DependencyBreaks)
	if len(out.ChangedParents) > 0 || len(out.DependencyBreaks) > 0 {
		out.Status = "geometric-attachment-drift-held-not-qualified"
	}
	if out.StableGeometricParents+out.UnresolvedAttachments+len(out.ChangedParents) != out.Persistent {
		return out, fmt.Errorf("attachment accounting mismatch")
	}
	return out, nil
}
func writeParentageAudit(path string, a ParentageAudit) error {
	b, err := json.MarshalIndent(a, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(b, '\n'), 0644)
}
