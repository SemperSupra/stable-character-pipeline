package avobserver

import (
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"strings"
	"testing"
)

func proxyGLB() []byte {
	b := []byte(`{"asset":{"version":"2.0"}} `)
	for len(b)%4 != 0 {
		b = append(b, ' ')
	}
	out := make([]byte, 20+len(b))
	copy(out, []byte("glTF"))
	binary.LittleEndian.PutUint32(out[4:], 2)
	binary.LittleEndian.PutUint32(out[8:], uint32(len(out)))
	binary.LittleEndian.PutUint32(out[12:], uint32(len(b)))
	binary.LittleEndian.PutUint32(out[16:], 0x4e4f534a)
	copy(out[20:], b)
	return out
}
func proxyEvidence() HoofEvidence {
	v := HoofEvidence{Schema: "equine.foot.science.v1", Source: "native_evaluated_skin_mesh",
		Frames: 48, SourceModel: "original_pony.glb", AssumedGroundZ: hoofGroundZ, NearThreshold: hoofNearM,
		SkateThreshold: hoofSkateM, PenetrationThreshold: hoofPenetrationM, SwingThreshold: hoofSwingM,
		ScientificVerdict: "NO_FAILURE_DETECTED_CONTACT_STILL_UNKNOWN", Trajectories: map[string][]HoofPoint{}}
	c := fixtureClock()
	for _, name := range hoofNames {
		pts := make([]HoofPoint, 48)
		for i := 0; i < 48; i++ {
			pts[i] = HoofPoint{Frame: i + 1, X: 0, Y: 0, MinZ: hoofGroundZ + 0.09}
		}
		for _, ev := range c.Events {
			if hoofNames[ev.Foot] == name {
				pts[ev.Frame].MinZ = hoofGroundZ + 0.01
			}
		}
		v.Trajectories[name] = pts
	}
	return v
}
func proxyRun(t *testing.T, c Clock, v HoofEvidence, expectedSHA string) (ProxyReceipt, error) {
	t.Helper()
	report, err := json.Marshal(v)
	if err != nil {
		t.Fatal(err)
	}
	return CheckContactProxy(c, report, proxyGLB(), "original_pony.glb", expectedSHA)
}
func TestProxyAcceptanceDoesNotClaimPhysicalContact(t *testing.T) {
	glb := proxyGLB()
	sha := fmt.Sprintf("%x", sha256.Sum256(glb))
	r, err := proxyRun(t, fixtureClock(), proxyEvidence(), sha)
	if err != nil {
		t.Fatal(err)
	}
	if r.Verdict != "NO_PROXY_CONTRADICTION_CONTACT_UNKNOWN" || r.ContactTruth != "UNKNOWN_NO_FORCE_SENSOR" || r.PlannedEventCount != 4 {
		t.Fatalf("false contact claim: %+v", r)
	}
}
func TestHoofProxyIndependentNegativeControls(t *testing.T) {
	glb := proxyGLB()
	sha := fmt.Sprintf("%x", sha256.Sum256(glb))
	cases := []struct {
		name      string
		mutate    func(*HoofEvidence)
		wantFail  bool
		wantError bool
	}{
		{"hover on planned strike", func(v *HoofEvidence) { p := v.Trajectories["front_L_hoof"]; p[12].MinZ = hoofGroundZ + 0.09 }, true, false},
		{"penetration", func(v *HoofEvidence) { p := v.Trajectories["hind_R_hoof"]; p[24].MinZ = hoofGroundZ - 0.04 }, true, false},
		{"skate pair", func(v *HoofEvidence) {
			p := v.Trajectories["front_L_hoof"]
			p[13].MinZ = hoofGroundZ + 0.01
			p[13].X = 0.25
		}, true, false},
		{"false source science pass", func(v *HoofEvidence) { v.ScientificVerdict = "FOOT_CONTACT_PROXY_FAIL" }, true, false},
		{"wrong ground", func(v *HoofEvidence) { v.AssumedGroundZ = 0 }, false, true},
		{"missing hoof", func(v *HoofEvidence) { delete(v.Trajectories, "front_R_hoof") }, false, true},
		{"missing frame", func(v *HoofEvidence) { v.Trajectories["hind_L_hoof"] = v.Trajectories["hind_L_hoof"][:47] }, false, true},
		{"wrong frame index", func(v *HoofEvidence) { v.Trajectories["hind_R_hoof"][0].Frame = 0 }, false, true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			v := proxyEvidence()
			tc.mutate(&v)
			r, err := proxyRun(t, fixtureClock(), v, sha)
			if tc.wantError {
				if err == nil {
					t.Fatalf("accepted broken evidence: %+v", r)
				}
				return
			}
			if err != nil {
				t.Fatal(err)
			}
			if tc.wantFail && r.Verdict != "FAIL_PROXY_CONTRADICTS_PLANNED_AUDIO" {
				t.Fatalf("missed defect: %+v", r)
			}
		})
	}
}
func TestProxySourceBindingAndHostileJSON(t *testing.T) {
	c := fixtureClock()
	v := proxyEvidence()
	data, _ := json.Marshal(v)
	glb := proxyGLB()
	sum := fmt.Sprintf("%x", sha256.Sum256(glb))
	for _, x := range []struct {
		name          string
		glb           []byte
		filename, sha string
	}{
		{"wrongSHA", glb, "original_pony.glb", strings.Repeat("0", 64)},
		{"wrongName", glb, "wrong.glb", sum},
		{"wrongGLB", bytes.Repeat([]byte("x"), 40), "original_pony.glb", sum},
		{"missingPin", glb, "original_pony.glb", ""},
	} {
		t.Run(x.name, func(t *testing.T) {
			if _, err := CheckContactProxy(c, data, x.glb, x.filename, x.sha); err == nil {
				t.Fatal("accepted unbound source")
			}
		})
	}
	for _, bad := range [][]byte{
		append(append([]byte{}, data...), []byte("{}")...),
		bytes.Replace(data, []byte(`"frames":48`), []byte(`"frames":48,"frames":48`), 1),
		bytes.Replace(data, []byte(`"min_z":`), []byte(`"min_z":0,"min_z":`), 1),
		bytes.Replace(data, []byte(`"min_z":`), []byte(`"min_z":1e999,"unused":`), 1),
		[]byte(`{"schema":"equine.foot.science.v1"}`),
	} {
		if _, err := ParseHoofEvidence(bad); err == nil {
			t.Fatal("accepted forged report")
		}
	}
	c.Events[1].Sample++
	if _, err := CheckContactProxy(c, data, glb, "original_pony.glb", sum); err == nil {
		t.Fatal("accepted clock tamper")
	}
}
