package avobserver

import (
	"encoding/binary"
	"math"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func guardPulse(at []int, gain float64) []int16 {
	p := make([]int16, 96000)
	for _, start := range at {
		for i := 0; i < 480 && i+start < len(p); i++ {
			sample := .36 * gain * math.Exp(-float64(i)/160) * (math.Sin(2*math.Pi*float64(i)*181/Rate) + .18*math.Sin(2*math.Pi*float64(i)*921/Rate))
			p[start+i] += int16(math.Round(32767 * sample))
		}
	}
	return p
}
func guardCloseClock() Clock {
	c := fixtureClock()
	c.Events = c.Events[:2]
	c.Events[0].Frame = 4
	c.Events[0].Sample = 8000
	c.Events[1].Frame = 5
	c.Events[1].Sample = 10000
	return c
}
func TestDomainGuardRejectAbstainAndAccept(t *testing.T) {
	std := fixtureClock()
	tc := []struct {
		name string
		c    Clock
		p    []int16
		want string
	}{
		{"supported dry beats", std, guardPulse([]int{0, 24000, 48000, 72000}, 1), "ACCEPT_SYNTHETIC_ONLY"},
		{"encoded-silence equivalent", std, guardPulse(nil, 1), "REJECT_SILENT_PCM"},
		{"missing beat", std, guardPulse([]int{0, 24000, 72000}, 1), "REJECT_DETECTED_MISMATCH"},
		{"extra beat", std, guardPulse([]int{0, 24000, 48000, 62000, 72000}, 1), "REJECT_DETECTED_MISMATCH"},
		{"close separate valid", guardCloseClock(), guardPulse([]int{8000, 10000}, 1), "ABSTAIN_CLOSE_EVENTS"},
		{"quiet nonzero valid", std, guardPulse([]int{0, 24000, 48000, 72000}, .1), "ABSTAIN_LOW_LEVEL"},
	}
	for _, v := range tc {
		t.Run(v.name, func(t *testing.T) {
			r := GuardedObserve(v.c, v.p)
			if r.Decision != v.want {
				t.Fatalf("got=%s want=%s rms=%.4g reason=%s", r.Decision, v.want, r.MaxBinRMS, r.Reason)
			}
			if r.ContactTruth != "UNKNOWN_NO_FORCE_SENSOR" || r.AcousticRealism != "UNKNOWN" {
				t.Fatal("science overclaim")
			}
		})
	}
}
func TestDomainGuardFailClosedSourceAndClipping(t *testing.T) {
	c := fixtureClock()
	p := guardPulse([]int{0, 24000, 48000, 72000}, 1)
	c.Basis = "OBSERVED_CONTACT"
	r := GuardedObserve(c, p)
	if r.Decision != "REJECT_INVALID_SOURCE" {
		t.Fatal(r)
	}
	c = fixtureClock()
	r = GuardedObserve(c, p[:10000])
	if r.Decision != "REJECT_DURATION_MISMATCH" {
		t.Fatal(r)
	}
	p[6000] = 32767
	r = GuardedObserve(c, p)
	if r.Decision != "ABSTAIN_CLIPPED_PCM" {
		t.Fatal(r)
	}
}
func TestDomainGuardActualAAC(t *testing.T) {
	if _, err := exec.LookPath("ffmpeg"); err != nil {
		t.Skip("native CI must exercise AAC")
	}
	cases := []struct {
		name     string
		c        Clock
		at       []int
		gain     float64
		decision string
	}{
		{"four", fixtureClock(), []int{0, 24000, 48000, 72000}, 1, "ACCEPT_SYNTHETIC_ONLY"},
		{"close", guardCloseClock(), []int{8000, 10000}, 1, "ABSTAIN_CLOSE_EVENTS"},
		{"quiet", fixtureClock(), []int{0, 24000, 48000, 72000}, .1, "ABSTAIN_LOW_LEVEL"},
		{"silent", fixtureClock(), nil, 1, "REJECT_SILENT_PCM"},
	}
	for _, v := range cases {
		t.Run(v.name, func(t *testing.T) {
			d := t.TempDir()
			raw := filepath.Join(d, "pcm.raw")
			out := filepath.Join(d, "audio.m4a")
			p := guardPulse(v.at, v.gain)
			b := make([]byte, 2*len(p))
			for i, x := range p {
				binary.LittleEndian.PutUint16(b[2*i:], uint16(x))
			}
			if err := os.WriteFile(raw, b, 0600); err != nil {
				t.Fatal(err)
			}
			cmd := exec.Command("ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-f", "s16le", "-ar", "48000", "-ac", "1", "-i", raw, "-c:a", "aac", "-b:a", "160k", out)
			if log, err := cmd.CombinedOutput(); err != nil {
				t.Fatalf("encode %v %s", err, log)
			}
			samples, err := Decode(out, 3)
			if err != nil {
				t.Fatal(err)
			}
			r := GuardedObserve(v.c, samples)
			if r.Decision != v.decision {
				t.Fatalf("%s want %s reason=%s maxRMS=%f", r.Decision, v.decision, r.Reason, r.MaxBinRMS)
			}
		})
	}
}
func TestDomainGuardDoesNotConcealMalformedClock(t *testing.T) {
	c := guardCloseClock()
	c.Events[0].Frame = 99
	r := GuardedObserve(c, guardPulse([]int{8000, 10000}, 1))
	if !strings.HasPrefix(r.Decision, "REJECT_") {
		t.Fatal("bad clock must not be abstained")
	}
}
