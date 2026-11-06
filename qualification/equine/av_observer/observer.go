// Package avobserver independently measures transient onsets in decoded audio.
// Event metadata is a claim, not proof that the exported media contains sound.
package avobserver

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math"
	"sort"
)

const Rate = 48000
const Bin = 240               // 5 ms; explicitly calibrated to synthetic impulse fixtures only.
const MaxOffsetSamples = 1920 // 40 ms, AAC codec-tolerance research limit, not perception standard.

type Event struct {
	ActorID      string `json:"actor_id"`
	Gait         string `json:"gait"`
	Surface      string `json:"surface"`
	Foot         string `json:"foot"`
	Kind         string `json:"kind"`
	ContactState string `json:"contact_state"`
	Source       string `json:"source"`
	Frame        int    `json:"frame"`
	Sample       int64  `json:"sample"`
}
type Clock struct {
	ActorID        string  `json:"actor_id"`
	Gait           string  `json:"gait"`
	Schema         string  `json:"schema"`
	Basis          string  `json:"basis"`
	Evaluation     string  `json:"evaluation"`
	FPS            int     `json:"fps"`
	SampleRate     int     `json:"sample_rate"`
	FramesPerCycle int     `json:"frames_per_cycle"`
	Cycles         int     `json:"cycles"`
	Events         []Event `json:"events"`
}
type Matched struct {
	PlannedSample  int64   `json:"planned_sample"`
	ObservedSample int64   `json:"observed_sample"`
	OffsetMS       float64 `json:"offset_ms"`
}
type Receipt struct {
	Schema                string    `json:"schema"`
	Verdict               string    `json:"verdict"`
	SourceClass           string    `json:"source_class"`
	ContactEvidence       string    `json:"contact_evidence"`
	AnimalAcousticRealism string    `json:"animal_acoustic_realism"`
	AudioIdentity         string    `json:"audio_identity"`
	Fps                   int       `json:"fps"`
	SampleRate            int       `json:"sample_rate"`
	ExpectedFrames        int       `json:"expected_frames"`
	ExpectedEvents        int       `json:"expected_events"`
	ExpectedAudibleGroups int       `json:"expected_audible_groups"`
	ObservedOnsets        []int64   `json:"observed_onsets"`
	Matched               []Matched `json:"matched"`
	Reasons               []string  `json:"reasons"`
	DecodedPCMSHA256      string    `json:"decoded_pcm_sha256"`
}

func ParseClock(blob []byte) (Clock, error) {
	var c Clock
	if len(blob) > 2*1024*1024 {
		return c, errors.New("clock too large")
	}
	dec := json.NewDecoder(bytes.NewReader(blob))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&c); err != nil {
		return c, err
	}
	var rest any
	if err := dec.Decode(&rest); err != io.EOF {
		return c, errors.New("trailing clock content")
	}
	if c.Schema != "equine.contact.v1" || c.Basis != "SYNTHETIC_PLANNED" || c.Evaluation != "PLANNED_ONLY_NOT_EVALUATED_HOOF_CONTACT" {
		return c, errors.New("not admitted synthetic planned source")
	}
	if c.ActorID == "" || c.Gait == "" || c.SampleRate != Rate || c.FPS < 12 || c.FPS > 120 || Rate%c.FPS != 0 || c.FramesPerCycle < 12 || c.FramesPerCycle > 240 || c.Cycles < 1 || c.Cycles > 16 {
		return c, errors.New("unsupported timeline")
	}
	if c.Events == nil || len(c.Events) > 2048 {
		return c, errors.New("invalid event array")
	}
	total := c.FramesPerCycle * c.Cycles
	if total > 30*c.FPS {
		return c, errors.New("duration exceeds 30 seconds")
	}
	prev := int64(-1)
	seen := map[string]bool{}
	for _, ev := range c.Events {
		if ev.ActorID != c.ActorID || ev.Gait != c.Gait || (ev.Surface != "sand" && ev.Surface != "stone" && ev.Surface != "soil" && ev.Surface != "grass") || ev.Kind != "hoof_impact" || ev.ContactState != "planned_contact" || ev.Source != "SYNTHETIC_PLANNED" ||
			ev.Foot != "HL" && ev.Foot != "HR" && ev.Foot != "FL" && ev.Foot != "FR" ||
			ev.Frame < 0 || ev.Frame >= total || ev.Sample != int64(ev.Frame*(Rate/c.FPS)) || ev.Sample < prev {
			return c, fmt.Errorf("unadmitted event %+v", ev)
		}
		key := fmt.Sprintf("%d:%s", ev.Sample, ev.Foot)
		if seen[key] {
			return c, errors.New("duplicate event")
		}
		seen[key] = true
		prev = ev.Sample
	}
	return c, nil
}

// Onsets is independent of events, so missing/extra sounds cannot disappear by
// asking the planned event list where to look. Intended for dry hoof Foley,
// not a general soundtrack classifier or animal/vocalization validator.
func Onsets(pcm []int16) []int64 {
	bins := (len(pcm) + Bin - 1) / Bin
	rms := make([]float64, bins)
	for j := 0; j < bins; j++ {
		end := (j + 1) * Bin
		if end > len(pcm) {
			end = len(pcm)
		}
		var ss float64
		for _, s := range pcm[j*Bin : end] {
			f := float64(s) / 32768
			ss += f * f
		}
		rms[j] = math.Sqrt(ss / float64(end-j*Bin))
	}
	result := []int64{}
	last := -100
	for i, e := range rms {
		if e < 0.012 || i-last < 16 {
			continue
		} // audible floor and >=80ms refractory
		var baseline float64
		if i > 0 {
			start := i - 8
			if start < 0 {
				start = 0
			}
			for j := start; j < i; j++ {
				baseline += rms[j]
			}
			baseline /= float64(i - start)
		}
		if e < baseline*2.8 || e < 0.016 {
			continue
		}
		result = append(result, int64(i*Bin))
		last = i
	}
	return result
}

func Observe(c Clock, pcm []int16) (Receipt, error) {
	blob, _ := json.Marshal(c)
	checked, err := ParseClock(blob)
	if err != nil {
		return Receipt{}, err
	}
	r := Receipt{Schema: "equine.av.decoded-audio-observer.v1", SourceClass: "SYNTHETIC_PLANNED",
		ContactEvidence: "PLANNED_ONLY_NOT_PHYSICAL_CONTACT", AnimalAcousticRealism: "UNKNOWN",
		AudioIdentity: "UNIDENTIFIED_IMPULSE_TRANSIENTS", Fps: checked.FPS, SampleRate: Rate,
		ExpectedFrames: checked.FramesPerCycle * checked.Cycles, ExpectedEvents: len(checked.Events),
		ObservedOnsets: []int64{}, Matched: []Matched{}, Reasons: []string{}}
	durationSamples := r.ExpectedFrames * (Rate / checked.FPS)
	if len(pcm) < durationSamples-2048 || len(pcm) > durationSamples+2400 {
		return r, fmt.Errorf("decoded sample count %d is not aligned to expected %d", len(pcm), durationSamples)
	}
	b := make([]byte, len(pcm)*2)
	for i, s := range pcm {
		b[i*2] = byte(s)
		b[i*2+1] = byte(uint16(s) >> 8)
	}
	r.DecodedPCMSHA256 = fmt.Sprintf("%x", sha256.Sum256(b))
	expected := []int64{}
	for _, ev := range checked.Events {
		if len(expected) == 0 || expected[len(expected)-1] != ev.Sample {
			expected = append(expected, ev.Sample)
		}
	}
	r.ExpectedAudibleGroups = len(expected)
	observed := Onsets(pcm)
	r.ObservedOnsets = observed
	// Monotonic one-to-one grouping. Simultaneous hoof events are not separately
	// audible or individually attributable in a mono waveform.
	used := make([]bool, len(observed))
	for _, at := range expected {
		chosen := -1
		dist := int64(MaxOffsetSamples + 1)
		for j, got := range observed {
			if used[j] {
				continue
			}
			d := got - at
			if d < 0 {
				d = -d
			}
			if d < dist {
				dist = d
				chosen = j
			}
		}
		if chosen < 0 || dist > MaxOffsetSamples {
			r.Reasons = append(r.Reasons, fmt.Sprintf("missing onset near planned sample %d", at))
			continue
		}
		used[chosen] = true
		r.Matched = append(r.Matched, Matched{PlannedSample: at, ObservedSample: observed[chosen], OffsetMS: float64(observed[chosen]-at) * 1000 / Rate})
	}
	for j, v := range used {
		if !v {
			r.Reasons = append(r.Reasons, fmt.Sprintf("unplanned onset at sample %d", observed[j]))
		}
	}
	if len(r.Reasons) > 0 {
		r.Verdict = "FAIL_AUDIO_TRANSIENT_ALIGNMENT"
	} else {
		r.Verdict = "PASS_SYNTHETIC_TRANSIENT_ALIGNMENT_ONLY"
	}
	sort.Slice(r.Matched, func(i, j int) bool { return r.Matched[i].PlannedSample < r.Matched[j].PlannedSample })
	return r, nil
}
