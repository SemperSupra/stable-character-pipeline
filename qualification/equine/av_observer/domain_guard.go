package avobserver

// DomainGuard is an experimental fail-closed support screen for the *existing*
// synthetic, dry hoof-Foley inspector. It does not replace Observe and never
// converts a detector's FAIL into PASS. Unsupported evidence becomes ABSTAIN.
// Any actual acoustic identity, physical contact, or naturalness remains UNKNOWN.
import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"math"
)

const refractorySamples = 16 * Bin // Existing Onsets 80ms refractory; not an animal norm.
const onsetRMSFloor = .016         // Current fixed RMS onset floor, not an SPL standard.

type DomainReceipt struct {
	Schema                        string   `json:"schema"`
	Decision                      string   `json:"decision"`
	Reason                        string   `json:"reason"`
	SourceClass                   string   `json:"source_class"`
	DecodedPCMSHA256              string   `json:"decoded_pcm_sha256"`
	UniqueExpectedGroups          int      `json:"unique_expected_groups"`
	MinimumPositiveSpacingSamples int64    `json:"minimum_positive_spacing_samples"`
	MaxBinRMS                     float64  `json:"max_bin_rms"`
	ContactTruth                  string   `json:"contact_truth"`
	AcousticRealism               string   `json:"animal_acoustic_realism"`
	Underlying                    *Receipt `json:"underlying,omitempty"`
}

func GuardedObserve(c Clock, pcm []int16) DomainReceipt {
	r := DomainReceipt{Schema: "equine.av.dry-onset-domain.v1", SourceClass: "SYNTHETIC_PLANNED", ContactTruth: "UNKNOWN_NO_FORCE_SENSOR", AcousticRealism: "UNKNOWN", Decision: "REJECT_INVALID_SOURCE", Reason: "unverified source"}
	b := make([]byte, 2*len(pcm))
	for i, x := range pcm {
		binary.LittleEndian.PutUint16(b[2*i:], uint16(x))
	}
	h := sha256.Sum256(b)
	r.DecodedPCMSHA256 = hex.EncodeToString(h[:])
	blob, err := json.Marshal(c)
	if err != nil {
		return r
	}
	verified, err := ParseClock(blob)
	if err != nil {
		return r
	}
	if len(pcm) < verified.FramesPerCycle*verified.Cycles*(Rate/verified.FPS)-2048 || len(pcm) > verified.FramesPerCycle*verified.Cycles*(Rate/verified.FPS)+2400 {
		r.Decision = "REJECT_DURATION_MISMATCH"
		r.Reason = "decoded length mismatches pinned 48k clock"
		return r
	}
	groups := []int64{}
	for _, e := range verified.Events {
		if len(groups) == 0 || groups[len(groups)-1] != e.Sample {
			groups = append(groups, e.Sample)
		}
	}
	r.UniqueExpectedGroups = len(groups)
	if len(groups) > 1 {
		best := int64(math.MaxInt64)
		for i := 1; i < len(groups); i++ {
			if d := groups[i] - groups[i-1]; d > 0 && d < best {
				best = d
			}
		}
		r.MinimumPositiveSpacingSamples = best
	}
	peak := 0.
	nonzero := false
	clipped := false
	for j := 0; j < len(pcm); j += Bin {
		end := j + Bin
		if end > len(pcm) {
			end = len(pcm)
		}
		sum := 0.
		for _, v := range pcm[j:end] {
			if v != 0 {
				nonzero = true
			}
			if v >= 32760 || v <= -32760 {
				clipped = true
			}
			x := float64(v) / 32768.
			sum += x * x
		}
		rms := math.Sqrt(sum / float64(end-j))
		if rms > peak {
			peak = rms
		}
	}
	r.MaxBinRMS = peak
	if !nonzero {
		r.Decision = "REJECT_SILENT_PCM"
		r.Reason = "exact decoded silence"
		return r
	}
	if clipped {
		r.Decision = "ABSTAIN_CLIPPED_PCM"
		r.Reason = "saturated samples are outside dry fixture qualification"
		return r
	}
	if r.MinimumPositiveSpacingSamples > 0 && r.MinimumPositiveSpacingSamples < refractorySamples {
		r.Decision = "ABSTAIN_CLOSE_EVENTS"
		r.Reason = "independent planned impulses are closer than 80ms calibrated onset refractory"
		return r
	}
	if peak < onsetRMSFloor {
		r.Decision = "ABSTAIN_LOW_LEVEL"
		r.Reason = "nonzero decoded signal below fixed dry-onset RMS floor"
		return r
	}
	observed, err := Observe(verified, pcm)
	if err != nil {
		r.Decision = "REJECT_DETECTOR_ERROR"
		r.Reason = err.Error()
		return r
	}
	r.Underlying = &observed
	if observed.Verdict == "PASS_SYNTHETIC_TRANSIENT_ALIGNMENT_ONLY" {
		r.Decision = "ACCEPT_SYNTHETIC_ONLY"
		r.Reason = "detector matched supported dry impulses"
	} else {
		r.Decision = "REJECT_DETECTED_MISMATCH"
		r.Reason = "independent decoded onset mismatch"
	}
	return r
}
