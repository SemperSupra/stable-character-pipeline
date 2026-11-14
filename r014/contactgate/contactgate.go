// Package contactgate measures source-safe heel/ball/toe clearance and
// labelled stance slip on an exact quarter-frame world-space trajectory.
// It does not infer physical contact, anatomical realism or release quality.
package contactgate

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math"
)

const Schema = "r014.synthetic_contact_quarter_frame.v1"

type Vec3 [3]float64
type Sole struct {
	Heel Vec3 `json:"heel"`
	Ball Vec3 `json:"ball"`
	Toe  Vec3 `json:"toe"`
 LowestShoeVertex Vec3 `json:"lowest_shoe_vertex_world"`
 LowestVertexIndex int `json:"lowest_shoe_vertex_index"`
}
type Frame struct {
	Tick  int  `json:"quarter_tick"`
	Root  Vec3 `json:"root"`
	Left  Sole `json:"left"`
	Right Sole `json:"right"`
}
type Segment struct {
	Foot    string `json:"foot"`
	Support string `json:"support_marker"`
	Start   int    `json:"start_tick_inclusive"`
	End     int    `json:"end_tick_inclusive"`
}
type Ground struct {
	Normal        Vec3    `json:"unit_normal"`
	Offset        float64 `json:"plane_offset_world_units"`
	MetresPerUnit float64 `json:"metres_per_world_unit"`
}
type Policy struct {
	MaxPenetrationM         float64 `json:"max_penetration_m"`
	MaxSupportHoverM        float64 `json:"max_support_hover_m"`
	MaxStanceMarkerSpeedMPS float64 `json:"max_stance_marker_speed_mps"`
	MinStanceSeconds        float64 `json:"min_stance_segment_s"`
 ContactBandM float64 `json:"sole_contact_band_m"`
 MinStanceCoverageFraction float64 `json:"minimum_stance_coverage_fraction"`
}
type Record struct {
	Schema            string    `json:"schema"`
	SourceScope       string    `json:"source_scope"`
	Claim             string    `json:"claim"`
	SceneSHA256       string    `json:"scene_sha256"`
	MotionSHA256      string    `json:"motion_sha256"`
 SoleMeshSHA256 string `json:"sole_mesh_sha256"`
	CalibrationSHA256 string    `json:"calibration_sha256"`
	StanceLabelSHA256 string    `json:"stance_label_sha256"`
	PolicySHA256      string    `json:"policy_sha256"`
	FrameCount        int       `json:"whole_frames"`
	FrameRate         int       `json:"frames_per_second"`
	Substeps          int       `json:"samples_per_whole_frame"`
	Ground            Ground    `json:"ground"`
	Policy            Policy    `json:"policy"`
	Frames            []Frame   `json:"frames"`
	Stance            []Segment `json:"stance"`
}

// Trust is a registry context independently supplied to Evaluate. Its contents
// must be backed by real reviewer evidence outside this Go library.
type Trust struct {
	SceneSHA256         string
	MotionSHA256        string
 SoleMeshSHA256 string
	CalibrationSHA256   string
	StanceLabelSHA256   string
	PolicySHA256        string
	ReviewerProofSHA256 string
	Reviewed            bool
}
type Extent struct {
	MinimumM float64 `json:"min_clearance_m"`
	MaximumM float64 `json:"max_clearance_m"`
}
type Metrics struct {
	Schema                  string            `json:"schema"`
	Status                  string            `json:"status"`
	SampleCount             int               `json:"quarter_frame_samples"`
	StanceSegments          int               `json:"stance_segments"`
	StanceSpeeds            int               `json:"stance_velocity_samples"`
	MaxStanceMarkerSpeedMPS float64           `json:"max_stance_marker_speed_mps"`
	MaxSupportHoverM        float64           `json:"max_support_marker_clearance_m"`
 MaxSoleHoverM float64 `json:"max_stance_lowest_shoe_vertex_hover_m"`
 StanceContactCoverage map[string]float64 `json:"stance_lowest_shoe_coverage_fraction_by_foot"`
	MaxPenetrationM         float64           `json:"max_marker_penetration_m"`
	RootTravelM             float64           `json:"root_world_travel_m"`
	MarkerExtents           map[string]Extent `json:"heel_ball_toe_and_sole_extents_by_foot"`
	SourceRights            string            `json:"source_rights"`
	PhysicalContact         string            `json:"physical_pressure_contact"`
	Cinematic               string            `json:"cinematic_acceptance"`
	CanonicalCharacterPack  string            `json:"canonical_character_pack"`
}

func newMetrics() Metrics {
	return Metrics{
		Schema: "r014.contact_quarter_frame_diagnostic.v1",
		Status: "REJECT_OR_UNKNOWN", SourceRights: "SOURCE_AND_LICENSE_NOT_PROVEN_BY_NUMERICS",
		PhysicalContact: "UNKNOWN_NO_PRESSURE_OR_COLLISION_EVIDENCE",
		Cinematic:       "HOLD_HUMAN_REVIEW", CanonicalCharacterPack: "HOLD_OWNER_ONLY",
	}
}
func digest(s string) bool {
	b, e := hex.DecodeString(s)
	return len(s) == 64 && e == nil && len(b) == 32
}
func finite(x float64) bool { return !math.IsNaN(x) && !math.IsInf(x, 0) }
func vecOK(v Vec3) bool     { return finite(v[0]) && finite(v[1]) && finite(v[2]) }
func dot(a, b Vec3) float64 { return a[0]*b[0] + a[1]*b[1] + a[2]*b[2] }
func sub(a, b Vec3) Vec3    { return Vec3{a[0] - b[0], a[1] - b[1], a[2] - b[2]} }
func norm(a Vec3) float64   { return math.Sqrt(dot(a, a)) }
func policyDigest(p Policy) string {
	b, _ := json.Marshal(p)
	s := sha256.Sum256(b)
	return hex.EncodeToString(s[:])
}
func PolicyDigest(p Policy) string { return policyDigest(p) }
func DecodeStrict(data []byte) (Record, error) {
	var r Record
	d := json.NewDecoder(bytes.NewReader(data))
	d.DisallowUnknownFields()
	if e := d.Decode(&r); e != nil {
		return r, e
	}
	var x any
	if e := d.Decode(&x); e != io.EOF {
		return r, errors.New("concatenated or trailing JSON")
	}
	return r, nil
}
func marker(f Frame, foot, part string) Vec3 {
	sole := f.Left
	if foot == "right" {
		sole = f.Right
	}
	switch part {
	case "heel":
		return sole.Heel
	case "ball":
		return sole.Ball
	default:
		return sole.Toe
	}
}
func signedDistance(f Vec3, g Ground) float64 { return (dot(f, g.Normal) - g.Offset) * g.MetresPerUnit }
func horizontalSpeed(a, b Vec3, g Ground, fps, substeps int) float64 {
	d := sub(a, b)
	vertical := dot(d, g.Normal)
	sq := dot(d, d) - vertical*vertical
	if sq < 0 {
		sq = 0
	}
	return math.Sqrt(sq) * g.MetresPerUnit * float64(fps*substeps)
}
func allPoints(f Frame) map[string]Vec3 {
	return map[string]Vec3{
		"left/heel": f.Left.Heel, "left/ball": f.Left.Ball, "left/toe": f.Left.Toe,
  "left/lowest_shoe_vertex":f.Left.LowestShoeVertex,
		"right/heel": f.Right.Heel, "right/ball": f.Right.Ball, "right/toe": f.Right.Toe,
  "right/lowest_shoe_vertex":f.Right.LowestShoeVertex,
	}
}
func Evaluate(r Record, t Trust) (Metrics, error) {
	m := newMetrics()
	if r.Schema != Schema || r.SourceScope != "PROJECT_ORIGINAL_SYNTHETIC_RDTE_ONLY" || r.Claim != "DIAGNOSTIC_ONLY" {
		return m, errors.New("unsupported schema, source scope or claim")
	}
	if !t.Reviewed || !digest(t.ReviewerProofSHA256) ||
		!digest(r.SceneSHA256) || !digest(r.MotionSHA256) ||
		!digest(r.CalibrationSHA256) || !digest(r.StanceLabelSHA256) || !digest(r.PolicySHA256) || !digest(r.SoleMeshSHA256) ||
		t.SceneSHA256 != r.SceneSHA256 || t.MotionSHA256 != r.MotionSHA256 || t.SoleMeshSHA256 != r.SoleMeshSHA256 ||
		t.CalibrationSHA256 != r.CalibrationSHA256 || t.StanceLabelSHA256 != r.StanceLabelSHA256 ||
		t.PolicySHA256 != r.PolicySHA256 || t.PolicySHA256 != policyDigest(r.Policy) {
		return m, errors.New("independent source, labels, calibration or policy evidence not matched")
	}
	p := r.Policy
	if !finite(p.MaxPenetrationM) || p.MaxPenetrationM < 0 ||
		!finite(p.MaxSupportHoverM) || p.MaxSupportHoverM < 0 ||
		!finite(p.MaxStanceMarkerSpeedMPS) || p.MaxStanceMarkerSpeedMPS < 0 ||
		!finite(p.MinStanceSeconds) || p.MinStanceSeconds <= 0 ||
 !finite(p.ContactBandM)||p.ContactBandM<=0 ||
 !finite(p.MinStanceCoverageFraction)||p.MinStanceCoverageFraction<=0||p.MinStanceCoverageFraction>1 {
		return m, errors.New("unreviewable contact policy")
	}
	g := r.Ground
	if !vecOK(g.Normal) || math.Abs(dot(g.Normal, g.Normal)-1) > 1e-7 ||
		!finite(g.Offset) || !finite(g.MetresPerUnit) || g.MetresPerUnit <= 0 {
		return m, errors.New("ground normal, origin or metric scale uncalibrated")
	}
	// Source-specific R009 rep: 72 complete whole frames at 12 Hz with
	// every quarter-step present, inclusive of first and last full frames.
	if r.FrameCount != 72 || r.FrameRate != 12 || r.Substeps != 4 ||
		len(r.Frames) != (r.FrameCount-1)*r.Substeps+1 {
		return m, errors.New("missing/altered 72-frame 12-Hz quarter-frame observation")
	}
	for i, f := range r.Frames {
		if f.Tick != i || !vecOK(f.Root) || f.Left.LowestVertexIndex<0 || f.Right.LowestVertexIndex<0 {
			return m, fmt.Errorf("missing/reordered/nonfinite quarter sample %d", i)
		}
		for key, point := range allPoints(f) {
			if !vecOK(point) {
				return m, fmt.Errorf("nonfinite marker %s at tick %d", key, i)
			}
		}
	}
	if len(r.Stance) == 0 {
		return m, errors.New("no independently labelled stance")
	}
	seenFoot := map[string]bool{}
	occupied := map[string]map[int]bool{"left": {}, "right": {}}
	for _, segment := range r.Stance {
		if segment.Foot != "left" && segment.Foot != "right" {
			return m, errors.New("invalid stance foot")
		}
		if segment.Support != "heel" && segment.Support != "ball" && segment.Support != "toe" {
			return m, errors.New("invalid independently labelled support marker")
		}
		if segment.Start < 0 || segment.End >= len(r.Frames) || segment.End <= segment.Start ||
			float64(segment.End-segment.Start)/float64(r.FrameRate*r.Substeps) < p.MinStanceSeconds {
			return m, errors.New("short/invalid labelled support segment")
		}
		for tick := segment.Start; tick <= segment.End; tick++ {
			if occupied[segment.Foot][tick] {
				return m, errors.New("overlapping support labels")
			}
			occupied[segment.Foot][tick] = true
		}
		seenFoot[segment.Foot] = true
	}
	if !seenFoot["left"] || !seenFoot["right"] {
		return m, errors.New("missing independent support for a foot")
	}
	// Complete per-marker clearance interval, including unlabeled swing.
	m.MarkerExtents = map[string]Extent{}
	for key := range allPoints(r.Frames[0]) {
		m.MarkerExtents[key] = Extent{MinimumM: math.Inf(1), MaximumM: math.Inf(-1)}
	}
	for _, f := range r.Frames {
		for key, point := range allPoints(f) {
			d := signedDistance(point, g)
			ext := m.MarkerExtents[key]
			if d < ext.MinimumM {
				ext.MinimumM = d
			}
			if d > ext.MaximumM {
				ext.MaximumM = d
			}
			m.MarkerExtents[key] = ext
			if d < 0 && -d > m.MaxPenetrationM {
				m.MaxPenetrationM = -d
			}
		}
	}
	contactCount:=map[string]int{"left":0,"right":0}
 supportCount:=map[string]int{"left":0,"right":0}
 for _, seg := range r.Stance {
  for tick := seg.Start; tick <= seg.End; tick++ {
   supportCount[seg.Foot]++
   low:=r.Frames[tick].Left.LowestShoeVertex
   if seg.Foot=="right" {low=r.Frames[tick].Right.LowestShoeVertex}
   soleHeight:=signedDistance(low,g)
   if soleHeight>m.MaxSoleHoverM {m.MaxSoleHoverM=soleHeight}
   if math.Abs(soleHeight)<=p.ContactBandM {contactCount[seg.Foot]++}
			d := signedDistance(marker(r.Frames[tick], seg.Foot, seg.Support), g)
			if d > m.MaxSupportHoverM {
				m.MaxSupportHoverM = d
			}
			if tick > seg.Start {
				speed := horizontalSpeed(marker(r.Frames[tick], seg.Foot, seg.Support),
					marker(r.Frames[tick-1], seg.Foot, seg.Support), g, r.FrameRate, r.Substeps)
				if speed > m.MaxStanceMarkerSpeedMPS {
					m.MaxStanceMarkerSpeedMPS = speed
				}
				m.StanceSpeeds++
			}
		}
	}
	m.RootTravelM = 0
	for i := 1; i < len(r.Frames); i++ {
		m.RootTravelM += norm(sub(r.Frames[i].Root, r.Frames[i-1].Root)) * g.MetresPerUnit
	}
	m.SampleCount = len(r.Frames)
 m.StanceSegments = len(r.Stance)
 m.StanceContactCoverage=map[string]float64{}
 for _,side:=range []string{"left","right"} {
   m.StanceContactCoverage[side]=float64(contactCount[side])/float64(supportCount[side])
 }
	if m.MaxPenetrationM > p.MaxPenetrationM || m.MaxSupportHoverM > p.MaxSupportHoverM ||
		m.MaxStanceMarkerSpeedMPS > p.MaxStanceMarkerSpeedMPS ||
 m.MaxSoleHoverM>p.MaxSupportHoverM ||
 m.StanceContactCoverage["left"]<p.MinStanceCoverageFraction ||
 m.StanceContactCoverage["right"]<p.MinStanceCoverageFraction {
		m.Status = "RED_DECLARED_CONTACT_POLICY"
		return m, nil
	}
	m.Status = "WITHIN_DECLARED_NUMERIC_POLICY_ONLY__NO_PHYSICAL_OR_RELEASE_PASS"
	return m, nil
}
