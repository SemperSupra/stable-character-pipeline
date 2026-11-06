package main

// Bounded opt-in bridge between independently tested lumped-mass wind dynamics
// and actual serialized GLB morph weights. The four pre-existing spatial target
// directions are retained. Only the lateral pair is driven: this is ONE DOF,
// not tree mechanics, leaf flutter, XPBD, or measured botanical behavior.
import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math"
)

type PhysicalWindTrack struct {
	TimesS           []float32
	MorphWeights     []float32
	TargetAmplitudeM float32
	ReceiptSHA256    string
}

func BuildPhysicalWindTrack(s Preset, receipt WindProbeReceipt) (PhysicalWindTrack, error) {
	empty := PhysicalWindTrack{}
	if err := validate(s); err != nil {
		return empty, err
	}
	if receipt.PlantID != s.ID || receipt.Parameters.PlantID != s.ID {
		return empty, fmt.Errorf("wind trace species mismatch")
	}
	if math.Abs(receipt.Parameters.DurationS-float64(s.WindPeriod)) > 1e-6 {
		return empty, fmt.Errorf("wind and GLB clock mismatch")
	}
	// A caller-supplied/stored receipt must be recomputed, not blindly trusted.
	canonical, err := RunWindProbe(receipt.Parameters)
	if err != nil {
		return empty, err
	}
	receivedBytes, err := json.Marshal(receipt)
	if err != nil {
		return empty, err
	}
	expectedBytes, err := json.Marshal(canonical)
	if err != nil {
		return empty, err
	}
	if !bytes.Equal(receivedBytes, expectedBytes) {
		return empty, fmt.Errorf("wind trace disagrees with independent deterministic replay")
	}
	digest := sha256.Sum256(expectedBytes)
	n := len(canonical.Samples)
	if n < 5 || n > 5001 {
		return empty, fmt.Errorf("unexpected wind trace count")
	}
	amplitude := math.Max(float64(s.WindAmplitude), canonical.MaxAbsDisplacementM)
	if amplitude == 0 {
		amplitude = .001
	}
	if amplitude <= 0 || amplitude > float64(s.Height) || !finite(amplitude) {
		return empty, fmt.Errorf("wind target displacement outside geometry domain")
	}
	result := PhysicalWindTrack{TimesS: make([]float32, 0, 49), MorphWeights: make([]float32, 0, 49*4), TargetAmplitudeM: float32(amplitude), ReceiptSHA256: hex.EncodeToString(digest[:])}
	stride := (n - 1) / 48
	if stride < 1 {
		stride = 1
	}
	for i, sample := range canonical.Samples {
		if i%stride != 0 && i != n-1 {
			continue
		}
		x := sample.TipDisplacementM / amplitude
		if !finite(x) || math.Abs(x) > 1+1e-6 {
			return empty, fmt.Errorf("nonfinite/unbounded morph weight")
		}
		if x > 1 {
			x = 1
		}
		if x < -1 {
			x = -1
		}
		pos, neg := float32(0), float32(0)
		if x >= 0 {
			pos = float32(x)
		} else {
			neg = float32(-x)
		}
		result.TimesS = append(result.TimesS, float32(sample.TimeS))
		result.MorphWeights = append(result.MorphWeights, pos, neg, 0, 0)
	}
	if len(result.TimesS) < 3 || result.TimesS[0] != 0 || math.Abs(float64(result.TimesS[len(result.TimesS)-1])-float64(s.WindPeriod)) > 1e-5 {
		return empty, fmt.Errorf("invalid exported wind clock endpoints")
	}
	for i := 1; i < len(result.TimesS); i++ {
		if result.TimesS[i] <= result.TimesS[i-1] {
			return empty, fmt.Errorf("nonmonotonic physical wind time")
		}
	}
	return result, nil
}
