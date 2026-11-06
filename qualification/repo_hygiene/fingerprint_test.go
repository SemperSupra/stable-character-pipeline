package main

import (
	"strings"
	"testing"
	"time"
)

func testFingerprintManifest() FingerprintManifest {
	h := func(v byte) string { return strings.Repeat(string(v), 64) }
	return FingerprintManifest{Schema: "scp.ci.input-closure.v1", Workcell: "equine-native-30j-contact", Inputs: []FingerprintInput{
		{"source", "pony-producer", h('a')}, {"workflow", "workflow-yml", h('b')}, {"runtime", "blender-4.5.15", h('c')}, {"fixture", "hoof-v1", h('d')}, {"rights", "public-original-v1", h('e')}, {"observer", "hoof-metrics-v1", h('f')},
	}}
}
func testFingerprintProof(digest string) FingerprintProof {
	return FingerprintProof{Schema: "scp.ci.verified-technical-proof.v1", InputFingerprint: digest, RunID: 123, Execution: "success", ArtifactSHA256: strings.Repeat("f", 64), VerifiedBy: "authoritative-readonly-provider", VerifiedAt: "2026-11-06T10:00:00Z", ExpiresAt: "2026-11-13T10:00:00Z", ArtifactAvailable: true, TrustBoundaryQualified: true, NoSourceScopeDrift: true}
}
func TestFingerprintDeterministicAndNoWeakClosure(t *testing.T) {
	a := testFingerprintManifest()
	one, err := ExactInputFingerprint(a)
	if err != nil {
		t.Fatal(err)
	}
	a.Inputs[0], a.Inputs[5] = a.Inputs[5], a.Inputs[0]
	two, err := ExactInputFingerprint(a)
	if err != nil || one != two {
		t.Fatal("order changed digest", err)
	}
	a.Inputs[0].SHA256 = strings.Repeat("0", 64)
	three, err := ExactInputFingerprint(a)
	if err != nil || three == one {
		t.Fatal("content drift accepted", err)
	}
}
func TestFingerprintInvalidCases(t *testing.T) {
	changes := []func(*FingerprintManifest){
		func(m *FingerprintManifest) { m.Schema = "other" },
		func(m *FingerprintManifest) { m.Inputs = m.Inputs[:4] },
		func(m *FingerprintManifest) { m.Inputs[0].SHA256 = "not hash" },
		func(m *FingerprintManifest) { m.Inputs[0].SHA256 = strings.Repeat("A", 64) },
		func(m *FingerprintManifest) { m.Inputs[0].ID = "../escape" },
		func(m *FingerprintManifest) { m.Inputs = append(m.Inputs, m.Inputs[0]) },
		func(m *FingerprintManifest) { m.Inputs[2].Kind = "unknown" },
		func(m *FingerprintManifest) { m.Inputs[4].Kind = "source" },
	}
	for i, fn := range changes {
		m := testFingerprintManifest()
		fn(&m)
		if _, err := ExactInputFingerprint(m); err == nil {
			t.Fatalf("untrusted closure accepted %d", i)
		}
	}
}
func TestReuseDecisionIsReviewOnly(t *testing.T) {
	m := testFingerprintManifest()
	digest, _ := ExactInputFingerprint(m)
	p := testFingerprintProof(digest)
	now := time.Date(2026, 11, 6, 12, 0, 0, 0, time.UTC)
	d := EvaluateTechnicalEvidenceReuse(m, p, now)
	if d.Disposition != "REVIEW_EXACT_TECHNICAL_EVIDENCE_REUSE" || !d.TechnicalEvidenceOnly || d.OwnerMergeReleaseApproved {
		t.Fatalf("invalid decision %+v", d)
	}
}
func TestReuseFailClosedOnStaleForgedMissingProof(t *testing.T) {
	m := testFingerprintManifest()
	digest, _ := ExactInputFingerprint(m)
	now := time.Date(2026, 11, 6, 12, 0, 0, 0, time.UTC)
	modifications := []func(*FingerprintProof){
		func(p *FingerprintProof) { p.InputFingerprint = strings.Repeat("0", 64) },
		func(p *FingerprintProof) { p.RunID = 0 },
		func(p *FingerprintProof) { p.Execution = "failure" },
		func(p *FingerprintProof) { p.ArtifactSHA256 = "garbage" },
		func(p *FingerprintProof) { p.VerifiedBy = "untrusted-pr-author" },
		func(p *FingerprintProof) { p.ArtifactAvailable = false },
		func(p *FingerprintProof) { p.TrustBoundaryQualified = false },
		func(p *FingerprintProof) { p.NoSourceScopeDrift = false },
		func(p *FingerprintProof) { p.ExpiresAt = "2026-11-06T11:00:00Z" },
		func(p *FingerprintProof) { p.VerifiedAt = "2026-11-06T13:00:00Z" },
		func(p *FingerprintProof) { p.ExpiresAt = "invalid" },
	}
	for i, fn := range modifications {
		p := testFingerprintProof(digest)
		fn(&p)
		d := EvaluateTechnicalEvidenceReuse(m, p, now)
		if d.Disposition != "RUN_REQUIRED" || d.OwnerMergeReleaseApproved {
			t.Fatalf("unsound historical reuse case %d: %+v", i, d)
		}
	}
	m.Inputs[0].SHA256 = strings.Repeat("1", 64)
	if got := EvaluateTechnicalEvidenceReuse(m, testFingerprintProof(digest), now); got.Disposition != "RUN_REQUIRED" {
		t.Fatal("source change trusted")
	}
}
func TestBrokenVerifierCannotDeclarePromotion(t *testing.T) {
	m := testFingerprintManifest()
	digest, _ := ExactInputFingerprint(m)
	d := EvaluateTechnicalEvidenceReuse(m, testFingerprintProof(digest), time.Date(2026, 11, 6, 12, 0, 0, 0, time.UTC))
	if d.OwnerMergeReleaseApproved {
		t.Fatal("proof reuse cannot authorize promotion")
	}
}

func BenchmarkExactInputFingerprint(b *testing.B) {
	m := testFingerprintManifest()
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		if _, err := ExactInputFingerprint(m); err != nil {
			b.Fatal(err)
		}
	}
}
func BenchmarkTechnicalProofReuseReview(b *testing.B) {
	m := testFingerprintManifest()
	d, _ := ExactInputFingerprint(m)
	p := testFingerprintProof(d)
	now := time.Date(2026, 11, 6, 12, 0, 0, 0, time.UTC)
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		got := EvaluateTechnicalEvidenceReuse(m, p, now)
		if got.Disposition != "REVIEW_EXACT_TECHNICAL_EVIDENCE_REUSE" {
			b.Fatal(got)
		}
	}
}
