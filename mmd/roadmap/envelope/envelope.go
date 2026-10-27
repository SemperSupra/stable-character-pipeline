// Package envelope defines source-bound, research-only MMD qualification evidence.
// It deliberately does NOT parse PMX, VMD, glTF or authorize a source or release.
package envelope

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math"
	"regexp"
	"strings"
)

const Schema = "scp.mmd.proof-bundle.v1"

var safeID = regexp.MustCompile("^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$")
var lowerHash = regexp.MustCompile("^[0-9a-f]{64}$")

type SourceRights struct {
	AssetRights       string `json:"asset_rights"`
	EvidenceURI       string `json:"evidence_uri"`
	CloudAllowed      bool   `json:"cloud_allowed"`
	RedistributeAllowed bool `json:"redistribute_allowed"`
}

// FrameOrigin is a pointer because frame zero is valid, but omission is NOT.
type SourceSemantics struct {
	NativeFormat      string       `json:"native_format"`
	NativeBoneLabels  []string     `json:"native_bone_labels"`
	NativeMorphLabels []string     `json:"native_morph_labels"`
	Units             string       `json:"units"`
	MetersPerUnit     float64      `json:"meters_per_unit"`
	Axes              string       `json:"axes"`
	FPSNumerator      int          `json:"fps_numerator"`
	FPSDenominator    int          `json:"fps_denominator"`
	FrameOrigin       *int         `json:"frame_origin"`
	Rights            SourceRights `json:"rights"`
}

type FixtureSpec struct {
	ID          string          `json:"id"`
	SourceURI   string          `json:"source_uri"`
	SourceSHA256 string         `json:"source_sha256"`
	FrameCount  int             `json:"frame_count"`
	Semantics   SourceSemantics `json:"semantics"`
}

type EngineObservation struct {
	ID            string             `json:"id"`
	Engine        string             `json:"engine"`
	EngineVersion string             `json:"engine_version"`
	FixtureSHA256 string             `json:"fixture_sha256"`
	Frame         int                `json:"frame"`
	TimeSeconds   *float64           `json:"time_seconds"`
	Status        string             `json:"status"`
	Measured      map[string]float64 `json:"measured"`
	DeclaredLoss  []string           `json:"declared_loss"`
}

type MetricEvidence struct {
	ID            string   `json:"id"`
	ObservationID string   `json:"observation_id"`
	Oracle        string   `json:"oracle"`
	Status        string   `json:"status"`
	Units         string   `json:"units"`
	Value         *float64 `json:"value"`
}

type ProofBundle struct {
	Schema       string              `json:"schema"`
	Fixture      FixtureSpec         `json:"fixture"`
	Observations []EngineObservation `json:"observations"`
	Metrics      []MetricEvidence    `json:"metrics"`
	Verdict      string              `json:"verdict"`
}

// DecodeStrict rejects unknown JSON keys and trailing documents. Invariants
// are applied AFTER syntax/schema checks; this is NOT a file-hash attestation.
func DecodeStrict(data []byte) (ProofBundle, error) {
	var b ProofBundle
	d := json.NewDecoder(bytes.NewReader(data))
	d.DisallowUnknownFields()
	if err := d.Decode(&b); err != nil { return b, fmt.Errorf("proof JSON: %w", err) }
	var extra any
	if err := d.Decode(&extra); !errors.Is(err, io.EOF) {
		return b, errors.New("trailing JSON content")
	}
	if err := Validate(b); err != nil { return b, err }
	return b, nil
}

func result(s string) bool {
	switch s { case "PASS", "FAIL", "UNKNOWN", "NOT_TESTED", "BLOCKED": return true }
	return false
}
func uniqueLabels(a []string) bool {
	if a == nil { return false }
	seen := make(map[string]bool)
	for _, x := range a {
		if strings.TrimSpace(x)=="" || seen[x] { return false }
		seen[x]=true
	}
	return true
}

func Validate(b ProofBundle) error {
	if b.Schema != Schema { return errors.New("unexpected proof bundle schema") }
	f:=b.Fixture; s:=f.Semantics
	if !safeID.MatchString(f.ID) || strings.TrimSpace(f.SourceURI)=="" || !lowerHash.MatchString(f.SourceSHA256) || f.FrameCount<1 {
		return errors.New("fixture id, source, digest or frame count invalid")
	}
	if s.FrameOrigin==nil || s.FPSNumerator<=0 || s.FPSDenominator<=0 ||
		s.MetersPerUnit<=0 || math.IsNaN(s.MetersPerUnit) || math.IsInf(s.MetersPerUnit,0) {
		return errors.New("missing source frame origin, timebase or finite unit scale")
	}
	if s.NativeFormat!="PMX" && s.NativeFormat!="VMD" && s.NativeFormat!="VPD" && s.NativeFormat!="GLTF" {
		return errors.New("unknown native format")
	}
	if s.Units!="m" && s.Units!="cm" && s.Units!="mm" && s.Units!="source_unit" {
		return errors.New("unknown source unit; do not guess")
	}
	if s.Axes!="RH_Y_UP" && s.Axes!="RH_Z_UP" && s.Axes!="LH_Y_UP" && s.Axes!="LH_Z_UP" {
		return errors.New("unknown handedness or up-axis")
	}
	if !uniqueLabels(s.NativeBoneLabels) || !uniqueLabels(s.NativeMorphLabels) {
		return errors.New("native labels must be explicit, distinct, and preserved verbatim")
	}
	r:=s.Rights
	if r.AssetRights!="ORIGINAL_SYNTHETIC" && r.AssetRights!="RIGHTS_CLEARED_EXTERNAL" &&
		r.AssetRights!="UNKNOWN" && r.AssetRights!="RESTRICTED" {
		return errors.New("invalid asset rights state")
	}
	if strings.TrimSpace(r.EvidenceURI)=="" {
		return errors.New("missing rights evidence reference")
	}
	if r.AssetRights=="UNKNOWN" || r.AssetRights=="RESTRICTED" {
		if r.CloudAllowed || r.RedistributeAllowed { return errors.New("unadmitted source rights claimed") }
	}
	if b.Observations==nil || b.Metrics==nil { return errors.New("missing evidence collections") }
	if !result(b.Verdict) { return errors.New("invalid bundle verdict") }
	obs:=map[string]EngineObservation{}
	allPass:=len(b.Observations)>0 && len(b.Metrics)>0
	for _, o:= range b.Observations {
		if !safeID.MatchString(o.ID) || obs[o.ID].ID!="" || !safeID.MatchString(o.Engine) ||
			strings.TrimSpace(o.EngineVersion)=="" || o.FixtureSHA256!=f.SourceSHA256 ||
			o.Frame<*s.FrameOrigin || o.Frame>=*s.FrameOrigin+f.FrameCount || o.TimeSeconds==nil || !result(o.Status) ||
			o.DeclaredLoss==nil {
			return errors.New("invalid or duplicate engine observation, source binding, native time or loss disclosure")
		}
		expected:=float64(o.Frame-*s.FrameOrigin)*float64(s.FPSDenominator)/float64(s.FPSNumerator)
		if math.IsNaN(*o.TimeSeconds) || math.IsInf(*o.TimeSeconds,0) || math.Abs(*o.TimeSeconds-expected)>1e-6 {
			return errors.New("observation time/frame mismatch")
		}
		for k,v:=range o.Measured {
			if strings.TrimSpace(k)=="" || math.IsNaN(v) || math.IsInf(v,0) { return errors.New("invalid measured primitive") }
		}
		if o.Status=="PASS" && len(o.Measured)==0 { return errors.New("PASS observation without measured primitive") }
		if o.Status!="PASS" { allPass=false }
		obs[o.ID]=o
	}
	metrics:=map[string]bool{}
	for _, m:=range b.Metrics {
		o,exists:=obs[m.ObservationID]
		if !safeID.MatchString(m.ID) || metrics[m.ID] || !exists || strings.TrimSpace(m.Oracle)=="" ||
			strings.TrimSpace(m.Units)=="" || !result(m.Status) {
			return errors.New("invalid/duplicate metric, oracle or observation reference")
		}
		if m.Value!=nil && (math.IsNaN(*m.Value) || math.IsInf(*m.Value,0)) { return errors.New("nonfinite metric") }
		if m.Status=="PASS" && (m.Value==nil || o.Status!="PASS") {
			return errors.New("metric PASS requires measured value and PASS source observation")
		}
		if m.Status!="PASS" { allPass=false }
		metrics[m.ID]=true
	}
	if b.Verdict=="PASS" {
		if !allPass || !r.CloudAllowed || !r.RedistributeAllowed ||
			(r.AssetRights!="ORIGINAL_SYNTHETIC" && r.AssetRights!="RIGHTS_CLEARED_EXTERNAL") {
			return errors.New("premature PASS: inconclusive observations, metrics or source rights")
		}
	}
	return nil
}

// ContentDigest provides only a byte digest, not a source entitlement or
// independent witness of the file named in SourceURI.
func ContentDigest(data []byte) string {
	h:=sha256.Sum256(data)
	return hex.EncodeToString(h[:])
}
