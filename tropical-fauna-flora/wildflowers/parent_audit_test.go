package main

import "testing"

func TestParentAuditPreservesUnknownAndDetectsChangedParent(t *testing.T) {
	s := loadExtendedPreset(t, "quercus_robur")
	s.GrowthStage = .4
	a := build(s)
	s.GrowthStage = .95
	b := build(s)
	out, err := AuditGeometricParentCorrespondence(a, b)
	if err != nil {
		t.Fatal(err)
	}
	if out.GeneratorScopeContract != FloraSemanticScopeContract {
		t.Fatal("missing generator scope contract")
	}
	if out.Persistent < 100 || out.UnresolvedAttachments < 0 || len(out.ChangedParents) < 0 {
		t.Fatal("incomplete parent source audit")
	}
	if out.StableGeometricParents+out.UnresolvedAttachments+len(out.ChangedParents) != out.Persistent {
		t.Fatal("invalid accounting")
	}
	// The generated parent proof must not silently discard a change.
	found := false
	for i := len(b.Organs) - 1; i > 0; i-- {
		o := &b.Organs[i]
		if o.AttachmentVerified && o.Parent > 2 && o.ID > 3 {
			o.Parent = 1
			found = true
			break
		}
	}
	if !found {
		t.Fatal("no eligible synthetic attachment")
	}
	changed, err := AuditGeometricParentCorrespondence(a, b)
	if err != nil {
		t.Fatal(err)
	}
	if len(changed.ChangedParents) <= len(out.ChangedParents) {
		t.Fatal("semantic parent path drift not detected")
	}
	if changed.Status != "geometric-attachment-drift-held-not-qualified" {
		t.Fatal("drift not held")
	}
}
func TestParentAuditRejectsNonMatchingDNA(t *testing.T) {
	s := loadExtendedPreset(t, "zea_mays")
	s.GrowthStage = .4
	a := build(s)
	s.GrowthStage = .95
	s.Seed++
	if _, err := AuditGeometricParentCorrespondence(a, build(s)); err == nil {
		t.Fatal("changed specimen admitted")
	}
}
