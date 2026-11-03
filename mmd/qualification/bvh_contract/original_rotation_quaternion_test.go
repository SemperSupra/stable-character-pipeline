package bvh

import (
	"math"
	"strings"
	"testing"
)

func nearVec(a, b Vec3) bool {
	for i := 0; i < 3; i++ {
		if math.Abs(a[i]-b[i]) > 1e-8 {
			return false
		}
	}
	return true
}
func nearQuat(a, b QuaternionXYZW) bool {
	for i := 0; i < 4; i++ {
		if math.Abs(a[i]-b[i]) > 1e-8 {
			return false
		}
	}
	return true
}
func TestOriginalQuatCompoundZThenXMatchesObservedSourceFK(t *testing.T) {
	src := rotationSource(t, "0 0 0 90 90 0 0 0 0 0 0 0")
	m := qualifiedSynthetic(t, src, 1)
	ks, e := m.SourceRotations(1)
	if e != nil {
		t.Fatal(e)
	}
	if len(ks) != 3 || ks[0].Name != "Hips" || ks[1].Name != "Knee" || ks[2].Name != "Foot" {
		t.Fatalf("SOURCE_QUATERNION_ACTOR_ALIAS:%+v", ks)
	}
	want := QuaternionXYZW{.5, .5, .5, .5}
	if !nearQuat(ks[0].LocalXYZW, want) || !nearQuat(ks[2].WorldXYZW, want) {
		t.Fatalf("BVH_CHANNEL_ORDER_ROTATION_QUATERNION_FALSE_PASS:%+v", ks)
	}
	rot, e := QRotate(ks[0].WorldXYZW, Vec3{0, -1, 0})
	if e != nil {
		t.Fatal(e)
	}
	w, e := m.Evaluate(1)
	if e != nil {
		t.Fatal(e)
	}
	translated := Vec3{w[1].PositionMeters[0] - w[0].PositionMeters[0],
		w[1].PositionMeters[1] - w[0].PositionMeters[1],
		w[1].PositionMeters[2] - w[0].PositionMeters[2]}
	if !nearVec(rot, translated) || !nearVec(rot, Vec3{0, 0, -1}) {
		t.Fatalf("INDEPENDENT_QUATERNION_FK_DISAGREES_WITH_ACTUAL_BVH:%v %v", rot, translated)
	}
}
func TestSourceQuaternionDoesNotCommuteOrIgnoreJointChannelOrder(t *testing.T) {
	src := rotationSource(t, "0 0 0 90 90 0 0 0 0 0 0 0")
	m := qualifiedSynthetic(t, src, 1)
	a, e := m.SourceRotations(1)
	if e != nil {
		t.Fatal(e)
	}
	if strings.Count(src, "Zrotation Xrotation Yrotation") < 1 {
		t.Fatal("SOURCE_ORDER_FIXTURE_CHANGED")
	}
	other := qualifiedSynthetic(t, strings.Replace(src, "Zrotation Xrotation Yrotation", "Xrotation Zrotation Yrotation", 1), 1)
	b, e := other.SourceRotations(1)
	if e != nil {
		t.Fatal(e)
	}
	if nearQuat(a[0].LocalXYZW, b[0].LocalXYZW) {
		t.Fatal("SOURCE_NONCOMMUTATIVE_ROTATION_ORDER_IGNORED")
	}
	if !nearQuat(b[0].LocalXYZW, QuaternionXYZW{.5, -.5, .5, .5}) {
		t.Fatalf("WRONG_SOURCE_ROTATION_ORDER_SIGN:%v", b[0].LocalXYZW)
	}
}
func TestExplicit60To30DropsActualNontrivialIntermediateRotation(t *testing.T) {
	src := rotationSource(t, "0 0 0 90 90 0 0 0 0 0 0 0")
	m := qualifiedSynthetic(t, src, 1)
	imp, e := m.SourceRotations(1)
	if e != nil {
		t.Fatal(e)
	}
	if nearQuat(imp[0].LocalXYZW, QuaternionXYZW{0, 0, 0, 1}) {
		t.Fatal("INTERMEDIATE_SOURCE_ROTATION_NOT_PRESENT")
	}
	loss, e := m.SourceSynthetic60To30()
	if e != nil {
		t.Fatal(e)
	}
	if loss.Schema != "scp.r009.public-original-bvh-ordered-quaternion-loss.v1" ||
		loss.SourceFPS != 60 || loss.TargetFPS != 30 || loss.SourceFrames != 3 || loss.TargetFrames != 2 ||
		loss.SourceFrameOne != "DROPPED_30FPS_RESAMPLE_NOT_INTERPOLATED" ||
		loss.PhysicalRetarget != "NOT_RUN_SOURCE_QUATERNIONS_ONLY" ||
		loss.ProtectedR009 != "HELD_NOT_ACCEPTED" || len(loss.Keyframes) != 6 {
		t.Fatalf("SOURCE_CLOCK_LOSS_NOT_DECLARED:%+v", loss)
	}
	for i, key := range loss.Keyframes {
		if key.SourceFrame == 1 {
			t.Fatalf("SOURCE_INTERMEDIATE_ROTATION_FALSE_PRESERVED:%d", i)
		}
		if key.TargetFrame != i/3 || key.SourceFrame != 2*(i/3) {
			t.Fatalf("SOURCE_KEYFRAME_CLOCK_MISMATCH:%d %+v", i, key)
		}
	}
}
func TestSourceQuatRightsAndNumericNegativeFalsifiers(t *testing.T) {
	src := rotationSource(t, "0 0 0 90 90 0 0 0 0 0 0 0")
	m := qualifiedSynthetic(t, src, 1)
	if _, e := m.SourceRotations(-1); e == nil {
		t.Fatal("NEGATIVE_FRAME_FALSE_ACCEPT")
	}
	if _, e := m.SourceRotations(3); e == nil {
		t.Fatal("PAST_LAST_FRAME_FALSE_ACCEPT")
	}
	if _, e := (nilMotion()).SourceSynthetic60To30(); e == nil {
		t.Fatal("NIL_MOTION_ACCEPTED")
	}
	nonunit := QuaternionXYZW{0, 0, 0, 0}
	if _, e := QRotate(nonunit, Vec3{0, 1, 0}); e == nil {
		t.Fatal("ZERO_QUATERNION_ACCEPTED")
	}
	if _, e := qAxis('Z', math.Inf(1)); e == nil {
		t.Fatal("INFINITE_ROTATION_ACCEPTED")
	}
	if _, e := qAxis('U', 45); e == nil {
		t.Fatal("UNKNOWN_ROTATION_AXIS_ACCEPTED")
	}
	m.Frames[1][3] = math.NaN()
	if _, e := m.SourceRotations(1); e == nil {
		t.Fatal("NAN_SOURCE_CHANNEL_ACCEPTED")
	}
	m.Frames[1][3] = 90
	m.Rights = "HUMAN_CAPTURE_SOURCE"
	if _, e := m.SourceRotations(1); e == nil {
		t.Fatal("UNAUTHORIZED_REAL_MOTION_ISSUER_ACCEPTED")
	}
	if _, e := m.SourceSynthetic60To30(); e == nil {
		t.Fatal("UNAUTHORIZED_PROJECTION_ACCEPTED")
	}
}
func nilMotion() *Motion { return nil }
