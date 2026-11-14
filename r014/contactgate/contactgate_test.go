package contactgate

import (
	"encoding/json"
	"math"
	"strings"
	"testing"
)

func sha(s string) string { return strings.Repeat(s, 64) }
func sample() Record {
	p := Policy{MaxPenetrationM: .004, MaxSupportHoverM: .01,
		MaxStanceMarkerSpeedMPS: .05, MinStanceSeconds: .25,
  ContactBandM:.005,MinStanceCoverageFraction:.90}
	r := Record{Schema: Schema, SourceScope: "PROJECT_ORIGINAL_SYNTHETIC_RDTE_ONLY", Claim: "DIAGNOSTIC_ONLY",
		SceneSHA256: sha("a"), MotionSHA256: sha("b"), SoleMeshSHA256:sha("f"), CalibrationSHA256: sha("c"),
		StanceLabelSHA256: sha("d"), PolicySHA256: policyDigest(p),
		FrameCount: 72, FrameRate: 12, Substeps: 4,
		Ground: Ground{Normal: Vec3{0, 0, 1}, MetresPerUnit: 1}, Policy: p,
		Stance: []Segment{{Foot: "left", Support: "heel", Start: 0, End: 110},
			{Foot: "right", Support: "heel", Start: 140, End: 284}}}
	for i := 0; i < 285; i++ {
		r.Frames = append(r.Frames, Frame{Tick: i, Root: Vec3{float64(i) * .001, 0, 1},
			Left:  Sole{Heel: Vec3{0, 0, .001}, Ball: Vec3{.1, 0, .001}, Toe: Vec3{.2, 0, .001},LowestShoeVertex:Vec3{0,0,.001},LowestVertexIndex:1},
			Right: Sole{Heel: Vec3{0, 1, .001}, Ball: Vec3{.1, 1, .001}, Toe: Vec3{.2, 1, .001},LowestShoeVertex:Vec3{0,1,.001},LowestVertexIndex:1}})
	}
	return r
}
func trusted(r Record) Trust {
	return Trust{SceneSHA256: r.SceneSHA256, MotionSHA256: r.MotionSHA256,SoleMeshSHA256:r.SoleMeshSHA256,
		CalibrationSHA256: r.CalibrationSHA256, StanceLabelSHA256: r.StanceLabelSHA256,
		PolicySHA256: r.PolicySHA256, ReviewerProofSHA256: sha("e"), Reviewed: true}
}
func mustReject(t *testing.T, r Record, trust Trust) {
	t.Helper()
	m, e := Evaluate(r, trust)
	if e == nil {
		t.Fatalf("invalid evidence accepted: %+v", m)
	}
	if m.CanonicalCharacterPack != "HOLD_OWNER_ONLY" {
		t.Fatal("lost product HOLD")
	}
}
func TestStationarySyntheticSupportNoPhysicalClaim(t *testing.T) {
	r := sample()
	m, e := Evaluate(r, trusted(r))
	if e != nil {
		t.Fatal(e)
	}
	if m.Status != "WITHIN_DECLARED_NUMERIC_POLICY_ONLY__NO_PHYSICAL_OR_RELEASE_PASS" ||
		m.SampleCount != 285 || m.StanceSpeeds != 254 || m.RootTravelM < .28 ||
		m.PhysicalContact != "UNKNOWN_NO_PRESSURE_OR_COLLISION_EVIDENCE" ||
  m.StanceContactCoverage["left"]!=1||m.StanceContactCoverage["right"]!=1 {
		t.Fatal(m)
	}
}
func TestStanceSlipRed(t *testing.T) {
	r := sample()
	r.Frames[42].Left.Heel[0] += .1
	m, e := Evaluate(r, trusted(r))
	if e != nil || m.Status != "RED_DECLARED_CONTACT_POLICY" || m.MaxStanceMarkerSpeedMPS < 4 {
		t.Fatalf("slip missed %+v %v", m, e)
	}
}
func TestSupportHoverRed(t *testing.T) {
	r := sample()
	r.Frames[42].Left.Heel[2] = .05
	m, e := Evaluate(r, trusted(r))
	if e != nil || m.Status != "RED_DECLARED_CONTACT_POLICY" || m.MaxSupportHoverM < .04 {
		t.Fatalf("hover missed %+v %v", m, e)
	}
}
func TestPenetrationRed(t *testing.T) {
	r := sample()
	r.Frames[42].Left.Toe[2] = -.01
	m, e := Evaluate(r, trusted(r))
	if e != nil || m.Status != "RED_DECLARED_CONTACT_POLICY" || m.MaxPenetrationM < .009 {
		t.Fatalf("penetration missed %+v %v", m, e)
	}
}
func TestNaturalToeRiseOutsideHeelContactNotAutomaticallyRed(t *testing.T) {
	r := sample()
	r.Frames[42].Left.Toe[2] = .15
	m, e := Evaluate(r, trusted(r))
	if e != nil || m.Status != "WITHIN_DECLARED_NUMERIC_POLICY_ONLY__NO_PHYSICAL_OR_RELEASE_PASS" {
		t.Fatalf("unlabelled toe hover must be only an extent: %+v %v", m, e)
	}
}
func TestMissingQuarterTick(t *testing.T) {
	r := sample()
	r.Frames[63].Tick = 64
	mustReject(t, r, trusted(r))
}
func TestMissingQuarterSample(t *testing.T) {
	r := sample()
	r.Frames = append(r.Frames[:17], r.Frames[18:]...)
	mustReject(t, r, trusted(r))
}
func TestWrongFPS(t *testing.T) { r := sample(); r.FrameRate = 24; mustReject(t, r, trusted(r)) }
func TestWrongFrameCount(t *testing.T) {
	r := sample()
	r.FrameCount = 64
	mustReject(t, r, trusted(r))
}
func TestShortStanceFraud(t *testing.T) {
	r := sample()
	r.Stance[0].End = 2
	mustReject(t, r, trusted(r))
}
func TestOmittedRightStance(t *testing.T) {
	r := sample()
	r.Stance = r.Stance[:1]
	mustReject(t, r, trusted(r))
}
func TestOverlappingStanceIntervals(t *testing.T) {
	r := sample()
	r.Stance = append(r.Stance, Segment{Foot: "left", Support: "ball", Start: 60, End: 80})
	mustReject(t, r, trusted(r))
}
func TestUnsupportedFootContactLabel(t *testing.T) {
	r := sample()
	r.Stance[0].Support = "sole"
	mustReject(t, r, trusted(r))
}
func TestReflectedGroundNormalNotUnit(t *testing.T) {
	r := sample()
	r.Ground.Normal = Vec3{0, 0, 2}
	mustReject(t, r, trusted(r))
}
func TestMissingIndependentCalibration(t *testing.T) {
	r := sample()
	tr := trusted(r)
	tr.CalibrationSHA256 = ""
	mustReject(t, r, tr)
}
func TestMissingIndependentPolicyReview(t *testing.T) {
	r := sample()
	tr := trusted(r)
	tr.Reviewed = false
	mustReject(t, r, tr)
}
func TestCandidateThresholdRelaxationRejected(t *testing.T) {
	r := sample()
	tr := trusted(r)
	r.Policy.MaxStanceMarkerSpeedMPS = 1000
	mustReject(t, r, tr)
}
func TestUnsupportedProtectedSourceOnPublicGate(t *testing.T) {
	r := sample()
	r.SourceScope = "RENDERPEOPLE_A001"
	mustReject(t, r, trusted(r))
}
func TestNonfiniteToeRejected(t *testing.T) {
	r := sample()
	r.Frames[4].Right.Toe[1] = math.NaN()
	mustReject(t, r, trusted(r))
}
func TestGroundOffsetAndScale(t *testing.T) {
	r := sample()
	r.Ground.Offset = 5
	r.Ground.MetresPerUnit = .01
	for i := range r.Frames {
		f := &r.Frames[i]
		for _, v := range []*Vec3{&f.Left.Heel, &f.Left.Ball, &f.Left.Toe,&f.Left.LowestShoeVertex, &f.Right.Heel, &f.Right.Ball, &f.Right.Toe,&f.Right.LowestShoeVertex} {
			(*v)[2] = 5.1
		}
	}
	m, e := Evaluate(r, trusted(r))
	if e != nil || math.Abs(m.MarkerExtents["right/heel"].MinimumM-.001) > 1e-10 {
		t.Fatalf("units or plane wrong %+v %v", m, e)
	}
}
func TestStrictJSONDoesNotAdmitExtraFields(t *testing.T) {
	r := sample()
	b, e := json.Marshal(r)
	if e != nil {
		t.Fatal(e)
	}
	if _, e := DecodeStrict(b); e != nil {
		t.Fatal(e)
	}
	if _, e := DecodeStrict(append(b, b...)); e == nil {
		t.Fatal("concatenated json admitted")
	}
	bad := strings.Replace(string(b), "\"schema\":", "\"surprise\":1,\"schema\":", 1)
	if _, e := DecodeStrict([]byte(bad)); e == nil {
		t.Fatal("unknown field admitted")
	}
}

func TestLowestShoeMeshHoverRedDespiteFlatHeelMarkers(t *testing.T){
 r:=sample();r.Frames[42].Left.LowestShoeVertex[2]=.088406
 m,e:=Evaluate(r,trusted(r))
 if e!=nil||m.Status!="RED_DECLARED_CONTACT_POLICY"||m.MaxSoleHoverM<.088 {
  t.Fatalf("88mm sole hover missed %+v %v",m,e)
 }
}
func TestSoleCoverageRedEvenWhenPeakHoverWithinThreshold(t *testing.T){
 r:=sample()
 for i:=30;i<65;i++{r.Frames[i].Left.LowestShoeVertex[2]=.006}
 m,e:=Evaluate(r,trusted(r))
 if e!=nil||m.Status!="RED_DECLARED_CONTACT_POLICY"||
  m.MaxSoleHoverM>.01||m.StanceContactCoverage["left"]>=.9{
   t.Fatalf("false contact coverage pass %+v %v",m,e)
 }
}
func TestSoleVertexMissingIndexRejected(t *testing.T){
 r:=sample();r.Frames[42].Right.LowestVertexIndex=-1;mustReject(t,r,trusted(r))
}
func TestSoleMeshByteIdentityNotAdmitted(t *testing.T){
 r:=sample();tr:=trusted(r);r.SoleMeshSHA256=sha("b");mustReject(t,r,tr)
}
func TestCoveragePolicyCannotBeRelaxedByCandidate(t *testing.T){
 r:=sample();tr:=trusted(r);r.Policy.MinStanceCoverageFraction=.1;mustReject(t,r,tr)
}
func TestSoleClearanceExtentIndependentOfProxyHeel(t *testing.T){
 r:=sample();r.Frames[0].Right.LowestShoeVertex[2]=.009
 m,e:=Evaluate(r,trusted(r))
 if e!=nil||m.MarkerExtents["right/lowest_shoe_vertex"].MaximumM<.0089{
  t.Fatalf("did not measure mesh sole point %+v %v",m,e)
 }
}
