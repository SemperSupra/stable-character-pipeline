package avobserver

// This independent geometry-to-audio preflight can disprove a planned impact,
// but cannot prove force-bearing hoof contact, ground reaction or animal gait.
// It consumes the native evaluated-mesh report from equine/contact_eval and
// source-exact GLB bytes; no planned event may be silently promoted to observed.

import (
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math"
	"path/filepath"
)

const (
	hoofGroundZ      = -0.015
	hoofNearM        = 0.05
	hoofSkateM       = 0.03
	hoofPenetrationM = 0.015
	hoofSwingM       = 0.045
)

var hoofNames = map[string]string{
	"FL": "front_L_hoof", "FR": "front_R_hoof",
	"HL": "hind_L_hoof", "HR": "hind_R_hoof",
}

type HoofPoint struct {
	Frame int     `json:"frame"`
	X     float64 `json:"x"`
	Y     float64 `json:"y"`
	MinZ  float64 `json:"min_z"`
}
type HoofEvidence struct {
	Schema               string                 `json:"schema"`
	Source               string                 `json:"source"`
	AssumedGroundZ       float64                `json:"assumed_ground_z_m"`
	NearThreshold        float64                `json:"near_ground_threshold_m"`
	SkateThreshold       float64                `json:"skate_threshold_m_per_frame"`
	PenetrationThreshold float64                `json:"penetration_threshold_m"`
	SwingThreshold       float64                `json:"minimum_swing_clearance_m"`
	HoovesMissingSwing   int                    `json:"hooves_without_minimum_swing_clearance"`
	Frames               int                    `json:"frames"`
	ScientificVerdict    string                 `json:"scientific_verdict"`
	SourceModel          string                 `json:"source_model"`
	Trajectories         map[string][]HoofPoint `json:"evaluated_hoof_trajectories"`
}
type ProxyReceipt struct {
	Schema              string   `json:"schema"`
	Verdict             string   `json:"verdict"`
	ContactTruth        string   `json:"contact_truth"`
	SourceClass         string   `json:"source_class"`
	SourceGLBSHA256     string   `json:"source_glb_sha256"`
	HoofEvidenceSHA256  string   `json:"hoof_evidence_sha256"`
	PlannedEventCount   int      `json:"planned_event_count"`
	EventContradictions int      `json:"event_contradictions"`
	TotalSkatePairs     int      `json:"total_skate_pairs"`
	HoovesMissingSwing  int      `json:"hooves_missing_swing"`
	MaxPenetrationM     float64  `json:"max_penetration_m"`
	Reasons             []string `json:"reasons"`
}

// rejectDuplicateObjectKeys refuses ambiguous JSON evidence (including nested
// hoof observations), before typed decoding; Go's default map decode is last-wins.
func rejectDuplicateObjectKeys(data []byte) error {
	d := json.NewDecoder(bytes.NewReader(data))
	var walk func() error
	walk = func() error {
		tok, err := d.Token()
		if err != nil {
			return err
		}
		delim, ok := tok.(json.Delim)
		if !ok {
			return nil
		}
		switch delim {
		case '{':
			seen := make(map[string]bool)
			for d.More() {
				keyTok, err := d.Token()
				if err != nil {
					return err
				}
				k, ok := keyTok.(string)
				if !ok {
					return errors.New("malformed JSON key")
				}
				if seen[k] {
					return fmt.Errorf("duplicate JSON key %q", k)
				}
				seen[k] = true
				if err = walk(); err != nil {
					return err
				}
			}
			end, err := d.Token()
			if err != nil || end != json.Delim('}') {
				return errors.New("malformed JSON object")
			}
		case '[':
			for d.More() {
				if err := walk(); err != nil {
					return err
				}
			}
			end, err := d.Token()
			if err != nil || end != json.Delim(']') {
				return errors.New("malformed JSON array")
			}
		default:
			return errors.New("unexpected JSON close delimiter")
		}
		return nil
	}
	if err := walk(); err != nil {
		return err
	}
	if _, err := d.Token(); err != io.EOF {
		return errors.New("trailing or malformed JSON")
	}
	return nil
}

func ParseHoofEvidence(data []byte) (HoofEvidence, error) {
	var v HoofEvidence
	if len(data) == 0 || len(data) > 2*1024*1024 {
		return v, errors.New("invalid bounded hoof report")
	}
	if err := rejectDuplicateObjectKeys(data); err != nil {
		return v, err
	}
	// Existing pinned report also has separately computed per-foot summaries.
	// Do not use those as the truth source; recompute from native trajectories.
	var raw map[string]json.RawMessage
	if err := json.Unmarshal(data, &raw); err != nil {
		return v, err
	}
	for _, field := range []string{"schema", "source", "assumed_ground_z_m", "near_ground_threshold_m", "skate_threshold_m_per_frame", "penetration_threshold_m", "minimum_swing_clearance_m", "hooves_without_minimum_swing_clearance", "frames", "scientific_verdict", "source_model", "evaluated_hoof_trajectories"} {
		if _, found := raw[field]; !found {
			return v, fmt.Errorf("missing %s", field)
		}
	}
	if err := json.Unmarshal(data, &v); err != nil {
		return v, err
	}
	if v.Schema != "equine.foot.science.v1" || v.Source != "native_evaluated_skin_mesh" || v.Frames != 48 || v.SourceModel == "" {
		return v, errors.New("unsupported provenance/frames")
	}
	if v.AssumedGroundZ != hoofGroundZ || v.NearThreshold != hoofNearM || v.SkateThreshold != hoofSkateM || v.PenetrationThreshold != hoofPenetrationM || v.SwingThreshold != hoofSwingM {
		return v, errors.New("unexpected source-owned proxy thresholds")
	}
	if len(v.Trajectories) != len(hoofNames) {
		return v, errors.New("requires four hoof trajectories")
	}
	for _, name := range hoofNames {
		points, ok := v.Trajectories[name]
		if !ok || len(points) != 48 {
			return v, fmt.Errorf("missing/full-48 hoof %s", name)
		}
		for i, p := range points {
			if p.Frame != i+1 || (math.IsNaN(p.X) || math.IsInf(p.X, 0)) || (math.IsNaN(p.Y) || math.IsInf(p.Y, 0)) || (math.IsNaN(p.MinZ) || math.IsInf(p.MinZ, 0)) {
				return v, fmt.Errorf("invalid %s frame %d", name, i+1)
			}
		}
	}
	return v, nil
}

func ValidateGLB(data []byte) error {
	if len(data) < 20 || len(data) > 64*1024*1024 {
		return errors.New("GLB length invalid")
	}
	if !bytes.Equal(data[:4], []byte{'g', 'l', 'T', 'F'}) || binary.LittleEndian.Uint32(data[4:8]) != 2 || binary.LittleEndian.Uint32(data[8:12]) != uint32(len(data)) {
		return errors.New("invalid GLB magic/version/declared length")
	}
	if binary.LittleEndian.Uint32(data[16:20]) != 0x4e4f534a {
		return errors.New("GLB has no leading JSON chunk")
	}
	return nil
}

// CheckContactProxy is intentionally a falsifier, not a physics acceptance gate.
// Caller supplies source bytes and an independently pinned expected GLB SHA.
// Geometric source observations remain a proxy, not instrumented contact forces.
func CheckContactProxy(clock Clock, evidenceJSON, glb []byte, modelName, expectedModelSHA string) (ProxyReceipt, error) {
	r := ProxyReceipt{Schema: "equine.audio-contact-proxy.v1", SourceClass: "SOURCE_ORIGINAL_SYNTHETIC",
		ContactTruth: "UNKNOWN_NO_FORCE_SENSOR", Reasons: []string{}}
	b, err := json.Marshal(clock)
	if err != nil {
		return r, err
	}
	c, err := ParseClock(b)
	if err != nil {
		return r, err
	}
	if c.FPS != 24 || c.FramesPerCycle*c.Cycles != 48 {
		return r, errors.New("48f/24fps exact source required")
	}
	if err := ValidateGLB(glb); err != nil {
		return r, err
	}
	sum := fmt.Sprintf("%x", sha256.Sum256(glb))
	if len(expectedModelSHA) != 64 || expectedModelSHA != sum {
		return r, errors.New("source GLB SHA mismatch/missing independent pin")
	}
	evidence, err := ParseHoofEvidence(evidenceJSON)
	if err != nil {
		return r, err
	}
	if modelName == "" || filepath.Base(modelName) != modelName || evidence.SourceModel != modelName {
		return r, errors.New("hooves measured from a different model filename")
	}
	r.SourceGLBSHA256 = sum
	r.HoofEvidenceSHA256 = fmt.Sprintf("%x", sha256.Sum256(evidenceJSON))
	r.PlannedEventCount = len(c.Events)
	missingSwing := 0
	for _, name := range hoofNames {
		points := evidence.Trajectories[name]
		elevated := 0
		for i, p := range points {
			gap := p.MinZ - hoofGroundZ
			if gap > hoofSwingM {
				elevated++
			}
			penetration := math.Max(0, -gap)
			r.MaxPenetrationM = math.Max(r.MaxPenetrationM, penetration)
			if i > 0 {
				last := points[i-1]
				if gap <= hoofNearM && last.MinZ-hoofGroundZ <= hoofNearM {
					if math.Hypot(p.X-last.X, p.Y-last.Y) > hoofSkateM {
						r.TotalSkatePairs++
					}
				}
			}
		}
		if elevated == 0 {
			missingSwing++
		}
	}
	r.HoovesMissingSwing = missingSwing
	if missingSwing != evidence.HoovesMissingSwing {
		r.Reasons = append(r.Reasons, "source reported swing count conflicts with independent trajectories")
	}
	expectedSourceVerdict := "NO_FAILURE_DETECTED_CONTACT_STILL_UNKNOWN"
	if r.TotalSkatePairs > 0 || r.MaxPenetrationM > hoofPenetrationM || r.HoovesMissingSwing > 0 {
		expectedSourceVerdict = "FOOT_CONTACT_PROXY_FAIL"
		r.Reasons = append(r.Reasons, "independent whole-trajectory skate/penetration/swing proxy failed")
	}
	if evidence.ScientificVerdict != expectedSourceVerdict {
		r.Reasons = append(r.Reasons, "source-reported scientific verdict disagrees with independently recomputed proxy")
	}
	for _, ev := range c.Events {
		points := evidence.Trajectories[hoofNames[ev.Foot]]
		// Source observer Blender frames are 1-based; event clock is 0-based.
		point := points[ev.Frame]
		gap := point.MinZ - hoofGroundZ
		if gap > hoofNearM || gap < -hoofPenetrationM {
			r.EventContradictions++
			r.Reasons = append(r.Reasons, fmt.Sprintf("planned %s frame %d contradicted by native hoof minZ gap %.6fm", ev.Foot, ev.Frame, gap))
		}
	}
	if len(r.Reasons) > 0 {
		r.Verdict = "FAIL_PROXY_CONTRADICTS_PLANNED_AUDIO"
	} else {
		r.Verdict = "NO_PROXY_CONTRADICTION_CONTACT_UNKNOWN"
	}
	return r, nil
}
