package editable

import (
	"bytes"
	"encoding/xml"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestDefaultRoundTrip(t *testing.T) {
	p := Default()
	if e := p.Validate(); e != nil {
		t.Fatal(e)
	}
	b, e := p.MIDI()
	if e != nil {
		t.Fatal(e)
	}
	q, e := ImportMIDI(p, b)
	if e != nil {
		t.Fatal(e)
	}
	if !reflect.DeepEqual(q, p) {
		t.Fatal("MIDI notes changed on roundtrip")
	}
	score, e := p.MusicXML()
	if e != nil {
		t.Fatal(e)
	}
	var result struct{ XMLName xml.Name }
	if e := xml.Unmarshal(score, &result); e != nil {
		t.Fatal(e)
	}
	if result.XMLName.Local != "score-partwise" {
		t.Fatal("invalid MusicXML root")
	}
	if !strings.Contains(p.CsoundMusic(), "f 1 0 16384 10 1") {
		t.Fatal("missing source oscillator wavetable")
	}
	if !strings.Contains(p.CsoundMotor(), "vco2") {
		t.Fatal("Csound motor missing oscillator")
	}
}
func TestEditsAreReversible(t *testing.T) {
	p := Default()
	q, e := Change(p, "note[0].pitch", "62")
	if e != nil {
		t.Fatal(e)
	}
	if q.Notes[0].Pitch != 62 || p.Notes[0].Pitch != 60 {
		t.Fatal("edit mutated original source")
	}
	reverse, e := Change(q, "note[0].pitch", "60")
	if e != nil || !reflect.DeepEqual(reverse, p) {
		t.Fatal("reversal not exact", e)
	}
	modified, e := Change(p, "motor.end_hz", "350")
	if e != nil {
		t.Fatal(e)
	}
	if modified.CsoundMotor() == p.CsoundMotor() {
		t.Fatal("motor edit did not change editable synthesizer")
	}
	for _, bad := range []struct{ field, value string }{{"note[0].pitch", "900"}, {"note[0].pitch", "60.1"}, {"motor.gain", "nan"}, {"bad", "42"}, {"note[0].length_tick", "4800"}} {
		if _, e := Change(p, bad.field, bad.value); e == nil {
			t.Errorf("accepted invalid edit %+v", bad)
		}
	}
}
func TestInvalidSourcesAndMIDI(t *testing.T) {
	p := Default()
	p.Classification = "PRIVATE_FINAL_CHARACTER_VOICE"
	if e := p.Validate(); e == nil {
		t.Fatal("private source admitted")
	}
	p = Default()
	d := t.TempDir()
	if e := p.Export(filepath.Join(d, "bundle")); e != nil {
		t.Fatal(e)
	}
	if e := p.Export(filepath.Join(d, "bundle")); e == nil {
		t.Fatal("overwritten bundle")
	}
	b, e := os.ReadFile(filepath.Join(d, "bundle", "melody.mid"))
	if e != nil {
		t.Fatal(e)
	}
	cases := [][]byte{nil, []byte("unsafe"), append([]byte(nil), b[:20]...), append([]byte(nil), b...)}
	cases[3][12] = 0 // corrupt MIDI PPQ
	for i, bad := range cases {
		if _, e := ImportMIDI(p, bad); e == nil {
			t.Errorf("MIDI negative case %d admitted", i)
		}
	}
}
func TestExportSourcesAreReversible(t *testing.T) {
	p := Default()
	d := filepath.Join(t.TempDir(), "bundle")
	if e := p.Export(d); e != nil {
		t.Fatal(e)
	}
	q, e := Read(filepath.Join(d, "project.json"))
	if e != nil {
		t.Fatal(e)
	}
	if !reflect.DeepEqual(p, q) {
		t.Fatal("native canonical project changed")
	}
	midi, e := os.ReadFile(filepath.Join(d, "melody.mid"))
	if e != nil {
		t.Fatal(e)
	}
	r, e := ImportMIDI(q, midi)
	if e != nil || !reflect.DeepEqual(q, r) {
		t.Fatal("MIDI roundtrip not reversible")
	}
	for _, s := range []string{"mechanical_motor.csd", "musical_theme.csd", "melody.musicxml"} {
		b, e := os.ReadFile(filepath.Join(d, s))
		if e != nil || len(bytes.TrimSpace(b)) < 100 {
			t.Fatal("missing source", s, e)
		}
	}
}