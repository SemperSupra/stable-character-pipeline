package main

// Developmental source-path correspondence for the existing procedural plant
// families. This is NOT an observed or biologically validated organ lineage.
// Keys are stable only for matching generator version, species, seed and all
// fixed parameters. A key is never inferred from visual/mesh index proximity.
import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"sort"
)

type LineageEvent struct {
	Key      string `json:"semantic_key"`
	Kind     string `json:"kind"`
	Material string `json:"material"`
}

type DevelopmentalCrosswalk struct {
	Schema                  string         `json:"schema"`
	Status                  string         `json:"status"`
	Species                 string         `json:"species"`
	Seed                    int64          `json:"seed"`
	ImmutablePresetSHA256   string         `json:"immutable_preset_sha256"`
	EarlierStage            float32        `json:"earlier_stage"`
	LaterStage              float32        `json:"later_stage"`
	EarlierOrganSHA256      string         `json:"earlier_organ_sha256"`
	LaterOrganSHA256        string         `json:"later_organ_sha256"`
	Persistent              []LineageEvent `json:"persistent"`
	Introduced              []LineageEvent `json:"introduced"`
	Disappeared             []LineageEvent `json:"disappeared"`
	VisualValidationStatus  string         `json:"visual_validation_status"`
	BiologicalIdentityState string         `json:"biological_identity_state"`
}

func immutablePresetDigest(p Preset) (string, error) {
	// Only phenological phase may differ; no comparisons between differently
	// seeded plants or silently changed morphometric or physics inputs.
	p.GrowthStage = 1
	b, err := json.Marshal(p)
	if err != nil {
		return "", err
	}
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:]), nil
}

func CompareDevelopmentalStages(a, b *Model) (DevelopmentalCrosswalk, error) {
	x := DevelopmentalCrosswalk{
		Schema:                  "scp.flora.sourcepath-developmental-crosswalk.v1",
		Status:                  "source-path-correspondence-only-not-observed-ontogeny",
		VisualValidationStatus:  "unqualified",
		BiologicalIdentityState: "unknown",
		Persistent:              []LineageEvent{}, Introduced: []LineageEvent{}, Disappeared: []LineageEvent{},
	}
	if a == nil || b == nil {
		return x, fmt.Errorf("nil model")
	}
	if err := validate(a.S); err != nil {
		return x, fmt.Errorf("earlier preset: %w", err)
	}
	if err := validate(b.S); err != nil {
		return x, fmt.Errorf("later preset: %w", err)
	}
	if a.S.GrowthStage <= 0 || b.S.GrowthStage <= a.S.GrowthStage || b.S.GrowthStage > 1 {
		return x, fmt.Errorf("stage must strictly increase within (0,1]")
	}
	ah, err := immutablePresetDigest(a.S)
	if err != nil {
		return x, err
	}
	bh, err := immutablePresetDigest(b.S)
	if err != nil {
		return x, err
	}
	if ah != bh || a.S.Seed != b.S.Seed || a.S.ID != b.S.ID {
		return x, fmt.Errorf("different specimen or fixed parameters; no source-path comparison")
	}
	ar, err := a.graphReceipt()
	if err != nil {
		return x, err
	}
	br, err := b.graphReceipt()
	if err != nil {
		return x, err
	}
	lookup := func(in OrganGraphReceipt) (map[string]LineageEvent, error) {
		out := make(map[string]LineageEvent, len(in.Organs))
		for _, org := range in.Organs {
			if org.SemanticKey == "" || org.Scope == "" || org.Scope == "unscoped" {
				return nil, fmt.Errorf("missing generator-authored semantic scope")
			}
			if _, ok := out[org.SemanticKey]; ok {
				return nil, fmt.Errorf("duplicate semantic key %q", org.SemanticKey)
			}
			if math.IsNaN(float64(org.AnchorM[1])) || math.IsInf(float64(org.AnchorM[1]), 0) {
				return nil, fmt.Errorf("nonfinite organ anchor")
			}
			out[org.SemanticKey] = LineageEvent{Key: org.SemanticKey, Kind: org.Kind, Material: org.Material}
		}
		return out, nil
	}
	am, err := lookup(ar)
	if err != nil {
		return x, err
	}
	bm, err := lookup(br)
	if err != nil {
		return x, err
	}
	for key, early := range am {
		if late, ok := bm[key]; ok {
			if early != late {
				return x, fmt.Errorf("semantic key alias changed kind/material %s", key)
			}
			x.Persistent = append(x.Persistent, early)
		} else {
			x.Disappeared = append(x.Disappeared, early)
		}
	}
	for key, late := range bm {
		if _, ok := am[key]; !ok {
			x.Introduced = append(x.Introduced, late)
		}
	}
	order := func(z []LineageEvent) { sort.Slice(z, func(i, j int) bool { return z[i].Key < z[j].Key }) }
	order(x.Persistent)
	order(x.Introduced)
	order(x.Disappeared)
	x.Species = a.S.ID
	x.Seed = a.S.Seed
	x.ImmutablePresetSHA256 = ah
	x.EarlierStage, x.LaterStage = a.S.GrowthStage, b.S.GrowthStage
	x.EarlierOrganSHA256, x.LaterOrganSHA256 = ar.SHA256, br.SHA256
	return x, nil
}

func writeDevelopmentalCrosswalk(path string, x DevelopmentalCrosswalk) error {
	b, err := json.MarshalIndent(x, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(b, '\n'), 0644)
}
