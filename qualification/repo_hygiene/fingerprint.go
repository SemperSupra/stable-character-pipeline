package main

// An experimental, read-only exact-input fingerprint for expensive source-
// original GitHub Actions qualification. This DOES NOT skip mandatory CI or
// turn a historical green run into a new scientific/owner acceptance.
import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"regexp"
	"sort"
	"strings"
	"time"
)

var fingerprintSHA = regexp.MustCompile(`^[0-9a-f]{64}$`)
var fingerprintID = regexp.MustCompile(`^[a-zA-Z0-9][a-zA-Z0-9._/@+-]{0,199}$`)

// FingerprintInput uses a SHA256 of the *actual bytes* or an unambiguous
// digest of a source commit. The producer is not trusted to declare equivalence.
type FingerprintInput struct {
	Kind   string `json:"kind"`
	ID     string `json:"id"`
	SHA256 string `json:"sha256"`
}
type FingerprintManifest struct {
	Schema   string             `json:"schema"`
	Workcell string             `json:"workcell"`
	Inputs   []FingerprintInput `json:"inputs"`
}
type FingerprintProof struct {
	Schema                 string `json:"schema"`
	InputFingerprint       string `json:"input_fingerprint"`
	RunID                  int64  `json:"run_id"`
	Execution              string `json:"execution"`
	ArtifactSHA256         string `json:"artifact_sha256"`
	VerifiedBy             string `json:"verified_by"`
	VerifiedAt             string `json:"verified_at"`
	ExpiresAt              string `json:"expires_at"`
	ArtifactAvailable      bool   `json:"artifact_available"`
	TrustBoundaryQualified bool   `json:"trust_boundary_qualified"`
	NoSourceScopeDrift     bool   `json:"no_source_scope_drift"`
}
type FingerprintDecision struct {
	Schema                    string `json:"schema"`
	Disposition               string `json:"disposition"`
	Reason                    string `json:"reason"`
	InputFingerprint          string `json:"input_fingerprint"`
	TechnicalEvidenceOnly     bool   `json:"technical_evidence_only"`
	OwnerMergeReleaseApproved bool   `json:"owner_merge_release_approved"`
}

// normalizedInputClosure enforces required source, workflow, runtime, fixture,
// and rights digests rather than hashing only the newest PR commit.
func normalizedInputClosure(m FingerprintManifest) ([]FingerprintInput, error) {
	if m.Schema != "scp.ci.input-closure.v1" || !fingerprintID.MatchString(m.Workcell) {
		return nil, errors.New("unrecognized workcell or schema")
	}
	if len(m.Inputs) < 5 || len(m.Inputs) > 200 {
		return nil, errors.New("invalid bounded dependency closure")
	}
	kinds := map[string]bool{}
	seen := map[string]bool{}
	inputs := append([]FingerprintInput(nil), m.Inputs...)
	for _, x := range inputs {
		switch x.Kind {
		case "source", "workflow", "runtime", "fixture", "rights", "observer", "tool":
		default:
			return nil, fmt.Errorf("unknown dependency kind %s", x.Kind)
		}
		if !fingerprintID.MatchString(x.ID) || strings.Contains(x.ID, "..") || !fingerprintSHA.MatchString(x.SHA256) {
			return nil, errors.New("invalid identity or sha256")
		}
		key := x.Kind + "/" + x.ID
		if seen[key] {
			return nil, errors.New("duplicate input identity")
		}
		seen[key] = true
		kinds[x.Kind] = true
	}
	for _, k := range []string{"source", "workflow", "runtime", "fixture", "rights"} {
		if !kinds[k] {
			return nil, fmt.Errorf("missing required %s digest", k)
		}
	}
	sort.Slice(inputs, func(i, j int) bool {
		a, b := inputs[i], inputs[j]
		if a.Kind != b.Kind {
			return a.Kind < b.Kind
		}
		return a.ID < b.ID
	})
	return inputs, nil
}
func ExactInputFingerprint(m FingerprintManifest) (string, error) {
	inputs, err := normalizedInputClosure(m)
	if err != nil {
		return "", err
	}
	safe := FingerprintManifest{Schema: m.Schema, Workcell: m.Workcell, Inputs: inputs}
	blob, err := json.Marshal(safe)
	if err != nil {
		return "", err
	}
	s := sha256.Sum256(blob)
	return hex.EncodeToString(s[:]), nil
}
func EvaluateTechnicalEvidenceReuse(m FingerprintManifest, p FingerprintProof, now time.Time) FingerprintDecision {
	d := FingerprintDecision{Schema: "scp.ci.proof-reuse-review.v1", Disposition: "RUN_REQUIRED", Reason: "no validated reusable proof", TechnicalEvidenceOnly: true, OwnerMergeReleaseApproved: false}
	digest, err := ExactInputFingerprint(m)
	if err != nil {
		d.Reason = "invalid or incomplete dependency closure"
		return d
	}
	d.InputFingerprint = digest
	if p.Schema != "scp.ci.verified-technical-proof.v1" || p.InputFingerprint != digest {
		d.Reason = "proof missing or input fingerprint drift"
		return d
	}
	if p.RunID <= 0 || p.Execution != "success" || !fingerprintSHA.MatchString(p.ArtifactSHA256) || p.VerifiedBy != "authoritative-readonly-provider" || !p.ArtifactAvailable || !p.TrustBoundaryQualified || !p.NoSourceScopeDrift {
		d.Reason = "proof not independently verified, eligible, accessible or successful"
		return d
	}
	at, aerr := time.Parse(time.RFC3339, p.VerifiedAt)
	exp, eerr := time.Parse(time.RFC3339, p.ExpiresAt)
	if aerr != nil || eerr != nil || now.Before(at) || !now.Before(exp) || !exp.After(at) {
		d.Reason = "proof time/expiry unverifiable"
		return d
	}
	// A qualified exact-input result permits a human/automation REVIEW of whether
	// to reuse its evidence. The function NEVER waives a required CI check.
	d.Disposition = "REVIEW_EXACT_TECHNICAL_EVIDENCE_REUSE"
	d.Reason = "all dependencies match available qualified historic technical proof; no fresh-run or science admission implied"
	return d
}
