package main

// Experimental three-mode wind substrate: two uncoupled lateral tip modes
// and one synthetic foliage flutter mode. This is deliberately NOT a
// measured aeroelastic model, XPBD, or a biomechanical growth simulation.
// The independent, source-anchored leaf morph is a kinematic approximation.
import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math"
	"os"
)

type MultiWindReceipt struct {
	Schema      string           `json:"schema"`
	ModelStatus string           `json:"model_status"`
	PlantID     string           `json:"plant_id"`
	X           WindProbeReceipt `json:"x"`
	Z           WindProbeReceipt `json:"z"`
	Leaf        WindProbeReceipt `json:"leaf"`
}

type MultiWindTrack struct {
	TimesS       []float32
	Weights      []float32
	Amplitudes   [3]float32
	SourceSHA256 string
}

func SyntheticMultiWind(s Preset) (MultiWindReceipt, error) {
	x := SyntheticWindProfile(s)
	z := x
	z.WindMeanMPerS = -.45
	z.GustAmplitudeMPerS = 1.25
	z.GustPeriodS = 3.2
	// The third profile represents an invented, local leaf oscillator.
	// It is not scaled or asserted as measured for any botanical species.
	leaf := x
	leaf.MassKg = .004
	leaf.StiffnessNPerM = .7
	leaf.DampingNSPerM = .055
	leaf.ProjectedAreaM2 = .012
	leaf.WindMeanMPerS = .1
	leaf.GustAmplitudeMPerS = 1.6
	leaf.GustPeriodS = .8
	leaf.MaxDisplacementM = .08
	leaf.InitialDisplacementM = 0
	leaf.InitialVelocityMPerS = 0
	a, err := RunWindProbe(x)
	if err != nil {
		return MultiWindReceipt{}, err
	}
	b, err := RunWindProbe(z)
	if err != nil {
		return MultiWindReceipt{}, err
	}
	c, err := RunWindProbe(leaf)
	if err != nil {
		return MultiWindReceipt{}, err
	}
	return MultiWindReceipt{
		Schema:      "scp.flora.synthetic-three-mode.v1",
		ModelStatus: "unmeasured-independent-x-z-tip-and-leaf-oscillators-not-physical-validation",
		PlantID:     s.ID, X: a, Z: b, Leaf: c,
	}, nil
}

func BuildMultiWindTrack(s Preset, r MultiWindReceipt) (MultiWindTrack, error) {
	out := MultiWindTrack{}
	if err := validate(s); err != nil {
		return out, err
	}
	if r.Schema != "scp.flora.synthetic-three-mode.v1" || r.ModelStatus != "unmeasured-independent-x-z-tip-and-leaf-oscillators-not-physical-validation" || r.PlantID != s.ID {
		return out, fmt.Errorf("multiwind identity or qualification mismatch")
	}
	sources := []WindProbeReceipt{r.X, r.Z, r.Leaf}
	for _, sr := range sources {
		if sr.PlantID != s.ID || sr.Parameters.PlantID != s.ID || math.Abs(sr.Parameters.DurationS-float64(s.WindPeriod)) > 1e-6 {
			return out, fmt.Errorf("multiwind species or clock mismatch")
		}
		replay, err := RunWindProbe(sr.Parameters)
		if err != nil {
			return out, err
		}
		a, err := json.Marshal(sr)
		if err != nil {
			return out, err
		}
		b, err := json.Marshal(replay)
		if err != nil {
			return out, err
		}
		if !bytes.Equal(a, b) {
			return out, fmt.Errorf("multiwind source trace fails deterministic replay")
		}
		if len(sr.Samples) != 481 {
			return out, fmt.Errorf("unsupported multiwind sample count")
		}
	}
	if r.X.Parameters != SyntheticWindProfile(s) {
		return out, fmt.Errorf("multiwind x profile is not the pinned synthetic profile")
	}
	canonical, err := SyntheticMultiWind(s)
	if err != nil {
		return out, err
	}
	first, err := json.Marshal(r)
	if err != nil {
		return out, err
	}
	second, err := json.Marshal(canonical)
	if err != nil {
		return out, err
	}
	if !bytes.Equal(first, second) {
		return out, fmt.Errorf("multiwind profile drift detected")
	}
	h := sha256.Sum256(first)
	out.SourceSHA256 = hex.EncodeToString(h[:])
	out.Amplitudes = [3]float32{
		float32(math.Max(float64(s.WindAmplitude), r.X.MaxAbsDisplacementM)),
		float32(math.Max(float64(s.WindAmplitude)*.7, r.Z.MaxAbsDisplacementM)),
		float32(math.Max(.008, r.Leaf.MaxAbsDisplacementM)),
	}
	for _, am := range out.Amplitudes {
		if !(am > 0 && finite(float64(am)) && am <= s.Height) {
			return MultiWindTrack{}, fmt.Errorf("multiwind amplitude outside geometry budget")
		}
	}
	out.TimesS = make([]float32, 0, 49)
	out.Weights = make([]float32, 0, 49*6)
	for i := 0; i < 481; i += 10 {
		samples := []WindProbeSample{r.X.Samples[i], r.Z.Samples[i], r.Leaf.Samples[i]}
		for j := 1; j < 3; j++ {
			if math.Abs(samples[j].TimeS-samples[0].TimeS) > 1e-8 {
				return MultiWindTrack{}, fmt.Errorf("source clock divergence")
			}
		}
		out.TimesS = append(out.TimesS, float32(samples[0].TimeS))
		for axis, sample := range samples {
			val := sample.TipDisplacementM / float64(out.Amplitudes[axis])
			if !finite(val) || math.Abs(val) > 1.00001 {
				return MultiWindTrack{}, fmt.Errorf("multiwind weights out of domain")
			}
			if val > 1 {
				val = 1
			}
			if val < -1 {
				val = -1
			}
			out.Weights = append(out.Weights, float32(math.Max(0, val)), float32(math.Max(0, -val)))
		}
	}
	if len(out.TimesS) != 49 || len(out.Weights) != 49*6 || out.TimesS[0] != 0 || math.Abs(float64(out.TimesS[48])-float64(s.WindPeriod)) > 1e-5 {
		return MultiWindTrack{}, fmt.Errorf("invalid multiwind output clock")
	}
	return out, nil
}

func leafMorphDeltas(m *Model, material string, amplitude float32, polarity int) ([]V, error) {
	ge := m.G[material]
	if ge == nil {
		return nil, nil
	}
	deltas := make([]V, len(ge.P))
	if material != "leaf" {
		return deltas, nil
	}
	if amplitude <= 0 || !finite(float64(amplitude)) || polarity != 1 && polarity != -1 {
		return nil, fmt.Errorf("bad leaf flutter amplitude/polarity")
	}
	coverage := make([]bool, len(ge.P))
	foliageCount := 0
	for _, organ := range m.Organs {
		if organ.Material != "leaf" {
			continue
		}
		lo, hi := organ.VertexOffset, organ.VertexOffset+organ.VertexCount
		if lo < 0 || hi > len(ge.P) || hi <= lo {
			return nil, fmt.Errorf("bad leaf organ extent")
		}
		if organ.Kind != "leaf" {
			return nil, fmt.Errorf("non-leaf geometry in leaf material: %s", organ.Kind)
		}
		maxDist := float32(0)
		for _, p := range ge.P[lo:hi] {
			d := p.sub(organ.Anchor)
			radius := float32(math.Sqrt(float64(d.X*d.X + d.Y*d.Y + d.Z*d.Z)))
			if radius > maxDist {
				maxDist = radius
			}
		}
		if maxDist < 1e-7 {
			return nil, fmt.Errorf("degenerate leaf organ")
		}
		// Alternate transverse direction per leaf semantic key. This is a
		// stable authored flutter *shape*, not independent physical leaf DOF.
		hh := sha256.Sum256([]byte(organ.SemanticKey))
		sign := float32(1)
		if hh[0]&1 != 0 {
			sign = -1
		}
		for idx := lo; idx < hi; idx++ {
			if coverage[idx] {
				return nil, fmt.Errorf("overlapping foliage extents")
			}
			coverage[idx] = true
			p := ge.P[idx]
			r := p.sub(organ.Anchor)
			radius := float32(math.Sqrt(float64(r.X*r.X + r.Y*r.Y + r.Z*r.Z)))
			t := float64(radius / maxDist)
			bending := float32(t*t) * amplitude * float32(polarity) * sign
			if p.Y <= .001 || radius <= .00001 {
				bending = 0
			}
			deltas[idx] = V{.20 * bending, .75 * bending, .36 * bending}
		}
		foliageCount++
	}
	if foliageCount == 0 {
		return nil, fmt.Errorf("no recorded foliage organ for material leaf")
	}
	for _, v := range coverage {
		if !v {
			return nil, fmt.Errorf("unrecorded leaf geometry")
		}
	}
	return deltas, nil
}

func writeMultiWindReceipt(path string, r MultiWindReceipt) error {
	b, err := json.MarshalIndent(r, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(b, '\n'), 0644)
}
