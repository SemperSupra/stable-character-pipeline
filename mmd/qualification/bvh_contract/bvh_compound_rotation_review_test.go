package bvh

// Independent, original-authored rotation-order falsifiers against the #249
// production FK. These are synthetic coordinates, NOT human JCS/ROM.
import (
	"crypto/sha256"
	"fmt"
	"math"
	"strings"
	"testing"
)

func rotationSource(t *testing.T, replacement string) string {
	t.Helper()
	needle := "0.5 0 0 90 0 0 0 0 0 0 0 0"
	if strings.Count(originalFixture, needle) != 1 {
		t.Fatal("SOURCE_FIXTURE_SHAPE_CHANGED")
	}
	return strings.Replace(originalFixture, needle, replacement, 1)
}
func closeSynthetic(p Vec3, expected Vec3) bool {
	for i := 0; i < 3; i++ {
		if math.Abs(p[i]-expected[i]) > 1e-8 {
			return false
		}
	}
	return true
}
func qualifiedSynthetic(t *testing.T, s string, meters float64) *Motion {
	t.Helper()
	m, e := Parse([]byte(s), "ORIGINAL_SELF_AUTHORED_SYNTHETIC", meters)
	if e != nil {
		t.Fatal(e)
	}
	if m.Rights != "ORIGINAL_SELF_AUTHORED_SYNTHETIC" || m.MeterPerUnit != meters {
		t.Fatal("SOURCE_RIGHTS_OR_UNITS_NOT_PRESERVED")
	}
	digest := sha256.Sum256([]byte(s))
	if m.SourceSHA256 != fmt.Sprintf("%x", digest) {
		t.Fatal("SOURCE_BYTES_NOT_CUSTODIED")
	}
	return m
}
func TestCompoundXZRotationOrderedFK(t *testing.T) {
	// BVH root ordered channels Zrotation Xrotation Yrotation with values
	// Z=+90 X=+90 Y=0. Applied to child Y=-1 yields world Z=-1.
	s := rotationSource(t, "0 0 0 90 90 0 0 0 0 0 0 0")
	m := qualifiedSynthetic(t, s, 1)
	w, e := m.Evaluate(1)
	if e != nil {
		t.Fatal(e)
	}
	if !closeSynthetic(w[0].PositionMeters, Vec3{0, 0, 0}) ||
		!closeSynthetic(w[1].PositionMeters, Vec3{0, 0, -1}) ||
		!closeSynthetic(w[2].PositionMeters, Vec3{0, 0, -2}) {
		t.Fatalf("COMPOUND_ROTATION_ORDER_FK_FALSE_PASS: %+v", w)
	}
}
func TestReorderingSameNumericChannelsChangesPose(t *testing.T) {
	s := rotationSource(t, "0 0 0 90 90 0 0 0 0 0 0 0")
	m := qualifiedSynthetic(t, s, 1)
	w, e := m.Evaluate(1)
	if e != nil {
		t.Fatal(e)
	}
	// A syntactically valid new channel order is NOT equivalent when both
	// angles are nonzero, even though it has the same numeric frame row.
	alternate := strings.Replace(s, "Zrotation Xrotation Yrotation", "Xrotation Zrotation Yrotation", 1)
	if alternate == s {
		t.Fatal("MISSING_COMPOUND_CHANNELS")
	}
	other := qualifiedSynthetic(t, alternate, 1)
	v, e := other.Evaluate(1)
	if e != nil {
		t.Fatal(e)
	}
	if !closeSynthetic(v[1].PositionMeters, Vec3{1, 0, 0}) {
		t.Fatalf("CHANNEL_ORDER_FK_FALSE_PASS: %+v", v[1])
	}
	if closeSynthetic(v[1].PositionMeters, w[1].PositionMeters) {
		t.Fatal("SOURCE_CHANNEL_ORDER_MUTANT_ACCEPTED_AS_EQUIVALENT")
	}
}
func TestPositiveYRotationAndNestedOffsetSigns(t *testing.T) {
	s := rotationSource(t, "0 0 0 0 0 90 0 0 0 0 0 0")
	needle := "JOINT Foot {\n   OFFSET 0 -1 0"
	if strings.Count(s, needle) != 1 {
		t.Fatal("FOOT_OFFSET_FIXTURE_CHANGED")
	}
	s = strings.Replace(s, needle, "JOINT Foot {\n   OFFSET 0 0 -1", 1)
	m := qualifiedSynthetic(t, s, 1)
	w, e := m.Evaluate(1)
	if e != nil {
		t.Fatal(e)
	}
	if !closeSynthetic(w[1].PositionMeters, Vec3{0, -1, 0}) ||
		!closeSynthetic(w[2].PositionMeters, Vec3{-1, -1, 0}) {
		t.Fatalf("Y_ROTATION_AXIS_OR_HANDEDNESS_FALSE_PASS: %+v", w)
	}
}
func TestChildRotationAppliedOnlyToDescendants(t *testing.T) {
	s := rotationSource(t, "0 0 0 0 0 0 90 0 0 0 0 0")
	m := qualifiedSynthetic(t, s, 1)
	w, e := m.Evaluate(1)
	if e != nil {
		t.Fatal(e)
	}
	if !closeSynthetic(w[0].PositionMeters, Vec3{0, 0, 0}) ||
		!closeSynthetic(w[1].PositionMeters, Vec3{0, -1, 0}) ||
		!closeSynthetic(w[2].PositionMeters, Vec3{1, -1, 0}) {
		t.Fatalf("DESCENDANT_PARENT_FK_FALSE_PASS: %+v", w)
	}
}
func TestDeclaredScaleOnCompoundRotation(t *testing.T) {
	s := rotationSource(t, "0 0 0 90 90 0 0 0 0 0 0 0")
	m := qualifiedSynthetic(t, s, .025)
	w, e := m.Evaluate(1)
	if e != nil {
		t.Fatal(e)
	}
	if !closeSynthetic(w[2].PositionMeters, Vec3{0, 0, -.05}) {
		t.Fatalf("UNQUALIFIED_SOURCE_SCALE_FALSE_PASS: %+v", w[2])
	}
	if _, e = Parse([]byte(s), "HUMAN_CAPTURE_SOURCE", .025); e == nil {
		t.Fatal("UNAUTHORIZED_REAL_SOURCE_ADMITTED")
	}
	if _, e = Parse([]byte(s), "ORIGINAL_SELF_AUTHORED_SYNTHETIC", 0); e == nil {
		t.Fatal("IMPLICIT_METERS_PER_UNIT_ACCEPTED")
	}
}
