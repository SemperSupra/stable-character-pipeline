package avobserver

import (
	"bytes"
	"encoding/binary"
	"encoding/json"
	"math"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func fixtureClock() Clock {
	c := Clock{ActorID: "pony-black", Gait: "walk", Schema: "equine.contact.v1", Basis: "SYNTHETIC_PLANNED", Evaluation: "PLANNED_ONLY_NOT_EVALUATED_HOOF_CONTACT", FPS: 24, SampleRate: 48000, FramesPerCycle: 48, Cycles: 1, Events: []Event{}}
	for i, foot := range []string{"HL", "FL", "HR", "FR"} {
		c.Events = append(c.Events, Event{ActorID: "pony-black", Gait: "walk", Surface: "sand", Foot: foot, Kind: "hoof_impact", ContactState: "planned_contact", Source: "SYNTHETIC_PLANNED", Frame: i * 12, Sample: int64(i * 24000)})
	}
	return c
}
func synthetic(at []int) []int16 {
	pcm := make([]int16, 96000)
	for _, start := range at {
		for i := 0; i < 4800 && start+i < len(pcm); i++ {
			// Short natural decaying transient with mixed frequency content.
			t := float64(i) / 48000
			value := .33 * math.Exp(-t/.015) * (math.Sin(t*2*math.Pi*137) + .29*math.Sin(t*2*math.Pi*1000))
			n := int(pcm[start+i]) + int(math.Round(value*32767))
			if n > 32767 {
				n = 32767
			}
			if n < -32768 {
				n = -32768
			}
			pcm[start+i] = int16(n)
		}
	}
	return pcm
}
func TestObserveAdversarial(t *testing.T) {
	c := fixtureClock()
	tests := []struct {
		name   string
		events []int
		want   string
	}{
		{"valid", []int{0, 24000, 48000, 72000}, "PASS_"},
		{"silence", []int{}, "FAIL_"},
		{"missing beat", []int{0, 24000, 72000}, "FAIL_"},
		{"extra beat", []int{0, 24000, 48000, 62000, 72000}, "FAIL_"},
		{"late beat", []int{0, 24000, 48000 + 4800, 72000}, "FAIL_"},
		{"early beat", []int{0, 24000 - 4800, 48000, 72000}, "FAIL_"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			r, err := Observe(c, synthetic(tc.events))
			if err != nil {
				t.Fatal(err)
			}
			if !strings.HasPrefix(r.Verdict, tc.want) {
				t.Fatalf("%s; detected=%v; reasons=%v", r.Verdict, r.ObservedOnsets, r.Reasons)
			}
			if r.AnimalAcousticRealism != "UNKNOWN" || r.ContactEvidence != "PLANNED_ONLY_NOT_PHYSICAL_CONTACT" {
				t.Fatalf("overclaim: %+v", r)
			}
		})
	}
}
func TestSimultaneousFootfallIsOneAudioGroup(t *testing.T) {
	c := fixtureClock()
	c.Events[1].Frame = 0
	c.Events[1].Sample = 0
	c.Events[2].Frame = 24
	c.Events[2].Sample = 48000
	c.Events[3].Frame = 24
	c.Events[3].Sample = 48000
	r, err := Observe(c, synthetic([]int{0, 48000}))
	if err != nil {
		t.Fatal(err)
	}
	if r.Verdict != "PASS_SYNTHETIC_TRANSIENT_ALIGNMENT_ONLY" || r.ExpectedEvents != 4 || r.ExpectedAudibleGroups != 2 {
		t.Fatalf("%+v", r)
	}
}
func TestUnadmittedAndClockTamper(t *testing.T) {
	c := fixtureClock()
	tests := []func(*Clock){
		func(v *Clock) { v.Basis = "PHYSICALLY_OBSERVED" },
		func(v *Clock) { v.Events[0].Sample = 1 },
		func(v *Clock) { v.Events[1] = v.Events[0] },
		func(v *Clock) { v.Events[2].Frame = 999 },
		func(v *Clock) { v.FPS = 29 },
		func(v *Clock) { v.Cycles = 100 },
	}
	for i, change := range tests {
		z := c
		z.Events = append([]Event(nil), c.Events...)
		change(&z)
		b, _ := json.Marshal(z)
		if _, err := ParseClock(b); err == nil {
			t.Fatalf("tamper %d accepted", i)
		}
	}
	b, _ := json.Marshal(c)
	if _, err := ParseClock(append(b, []byte("{}")...)); err == nil {
		t.Fatal("trailing JSON accepted")
	}
	if _, err := ParseClock(bytes.Replace(b, []byte("\"basis\""), []byte("\"bogus\""), 1)); err == nil {
		t.Fatal("unknown key accepted")
	}
	if _, err := Observe(c, synthetic([]int{0})[:48000]); err == nil {
		t.Fatal("truncated audio accepted")
	}
}
func TestActualAACDecodeWithNegativeControls(t *testing.T) {
	if _, err := exec.LookPath("ffmpeg"); err != nil {
		t.Skip("FFmpeg unavailable; native codec qualification required in CI")
	}
	c := fixtureClock()
	for _, tc := range []struct {
		name   string
		events []int
		want   string
	}{
		{"native-aac-valid", []int{0, 24000, 48000, 72000}, "PASS_"},
		{"native-aac-silent", []int{}, "FAIL_"},
		{"native-aac-extra", []int{0, 24000, 48000, 62000, 72000}, "FAIL_"},
		{"native-aac-offset", []int{0, 24000, 52800, 72000}, "FAIL_"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			dir := t.TempDir()
			raw := filepath.Join(dir, "src.raw")
			out := filepath.Join(dir, "encoded.m4a")
			pcm := synthetic(tc.events)
			b := make([]byte, 2*len(pcm))
			for i, v := range pcm {
				binary.LittleEndian.PutUint16(b[2*i:], uint16(v))
			}
			if err := os.WriteFile(raw, b, 0600); err != nil {
				t.Fatal(err)
			}
			cmd := exec.Command("ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-f", "s16le", "-ar", "48000", "-ac", "1", "-i", raw, "-c:a", "aac", "-b:a", "160k", out)
			if msg, err := cmd.CombinedOutput(); err != nil {
				t.Fatalf("native AAC: %v: %s", err, msg)
			}
			decoded, err := Decode(out, 3)
			if err != nil {
				t.Fatal(err)
			}
			r, err := Observe(c, decoded)
			if err != nil {
				t.Fatal(err)
			}
			if !strings.HasPrefix(r.Verdict, tc.want) {
				t.Fatalf("verdict=%s onsets=%v reasons=%v", r.Verdict, r.ObservedOnsets, r.Reasons)
			}
		})
	}
}
