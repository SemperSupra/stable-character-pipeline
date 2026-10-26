package editable

import (
	"bytes"
	"encoding/binary"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

const Schema = "editable_audio.v1"
const Public = "PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL"
const PPQ = 480

type Note struct {
	Pitch      int `json:"pitch"`
	StartTick  int `json:"start_tick"`
	LengthTick int `json:"length_tick"`
	Velocity   int `json:"velocity"`
}
type Motor struct {
	StartHz float64 `json:"start_hz"`
	EndHz   float64 `json:"end_hz"`
	Gain    float64 `json:"gain"`
}
type Project struct {
	Schema         string `json:"schema"`
	ID             string `json:"id"`
	Classification string `json:"classification"`
	BPM            int    `json:"bpm"`
	Beats          int    `json:"beats"`
	Rate           int    `json:"sample_rate_hz"`
	Motor          Motor  `json:"motor"`
	Notes          []Note `json:"notes"`
}

func Default() Project {
	return Project{Schema: Schema, ID: "synthetic_audio_reauthoring", Classification: Public, BPM: 120, Beats: 16, Rate: 48000, Motor: Motor{StartHz: 78, EndHz: 215, Gain: 0.06}, Notes: []Note{{60, 0, 480, 82}, {64, 480, 480, 78}, {67, 960, 960, 85}, {65, 1920, 480, 82}, {64, 2400, 480, 76}, {62, 2880, 480, 79}, {60, 3360, 480, 85}, {67, 3840, 960, 78}, {65, 4800, 480, 81}, {64, 5280, 480, 79}, {62, 5760, 960, 80}, {60, 6720, 960, 82}}}
}
func (p Project) Validate() error {
	if p.Schema != Schema || p.Classification != Public || p.ID != "synthetic_audio_reauthoring" {
		return errors.New("unsupported schema, project ID or privacy classification")
	}
	if p.BPM < 40 || p.BPM > 240 || p.Beats < 4 || p.Beats > 64 || p.Beats%4 != 0 || p.Rate != 48000 {
		return errors.New("invalid tempo/length/sample rate")
	}
	m := p.Motor
	if math.IsNaN(m.StartHz) || math.IsNaN(m.EndHz) || math.IsNaN(m.Gain) || math.IsInf(m.StartHz, 0) || math.IsInf(m.EndHz, 0) || math.IsInf(m.Gain, 0) || m.StartHz < 35 || m.StartHz > 2500 || m.EndHz < 35 || m.EndHz > 2500 || m.Gain < 0.001 || m.Gain > 0.25 {
		return errors.New("invalid procedural motor parameters")
	}
	if len(p.Notes) == 0 || len(p.Notes) > 256 {
		return errors.New("invalid note count")
	}
	end := 0
	for _, n := range p.Notes {
		if n.Pitch < 36 || n.Pitch > 96 || n.Velocity < 1 || n.Velocity > 127 || n.StartTick < end || n.StartTick%120 != 0 || n.LengthTick < 120 || n.LengthTick%120 != 0 || n.StartTick+n.LengthTick > p.Beats*PPQ {
			return errors.New("invalid, overlapping, out-of-range or nonquantized note")
		}
		if n.StartTick/1920 != (n.StartTick+n.LengthTick-1)/1920 {
			return errors.New("notes crossing measures are not yet representable in musicxml export")
		}
		end = n.StartTick + n.LengthTick
	}
	return nil
}
func Read(path string) (Project, error) {
	f, e := os.Open(path)
	if e != nil {
		return Project{}, e
	}
	defer f.Close()
	d := json.NewDecoder(io.LimitReader(f, 1<<20))
	d.DisallowUnknownFields()
	var p Project
	if e = d.Decode(&p); e != nil {
		return p, e
	}
	var extra interface{}
	if e = d.Decode(&extra); e != io.EOF {
		return p, errors.New("trailing JSON")
	}
	return p, p.Validate()
}
func WriteNew(path string, data []byte) error {
	f, e := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if e != nil {
		return e
	}
	n, e := f.Write(data)
	closeErr := f.Close()
	if e != nil || closeErr != nil || n != len(data) {
		os.Remove(path)
		return errors.New("incomplete output")
	}
	return nil
}
func (p Project) Bytes() ([]byte, error) {
	if e := p.Validate(); e != nil {
		return nil, e
	}
	b, e := json.MarshalIndent(p, "", "  ")
	return append(b, '\n'), e
}
func Change(p Project, field, value string) (Project, error) {
	q := p
	q.Notes = append([]Note(nil), p.Notes...)
	n, e := strconv.ParseFloat(value, 64)
	if e != nil || math.IsNaN(n) || math.IsInf(n, 0) {
		return p, errors.New("bad edit value")
	}
	switch field {
	case "motor.start_hz":
		q.Motor.StartHz = n
	case "motor.end_hz":
		q.Motor.EndHz = n
	case "motor.gain":
		q.Motor.Gain = n
	default:
		var i int
		var k string
		if _, e = fmt.Sscanf(field, "note[%d].%s", &i, &k); e != nil || i < 0 || i >= len(q.Notes) {
			return p, errors.New("unknown edit path")
		}
		if n != math.Trunc(n) {
			return p, errors.New("note value must be integer")
		}
		switch k {
		case "pitch":
			q.Notes[i].Pitch = int(n)
		case "velocity":
			q.Notes[i].Velocity = int(n)
		case "start_tick":
			q.Notes[i].StartTick = int(n)
		case "length_tick":
			q.Notes[i].LengthTick = int(n)
		default:
			return p, errors.New("unknown note field")
		}
	}
	if e = q.Validate(); e != nil {
		return p, e
	}
	return q, nil
}
func duration(p Project) float64 { return float64(p.Beats) * 60 / float64(p.BPM) }
func (p Project) CsoundMotor() string {
	return fmt.Sprintf(`<CsoundSynthesizer>
<CsOptions>
</CsOptions>
<CsInstruments>
sr = 48000
ksmps = 32
nchnls = 2
0dbfs = 1
instr 1
kfreq line p4, p3, p5
asig vco2 p6, kfreq
kenv linseg 0, 0.03, 1, p3-0.06, 1, 0.03, 0
outs asig*kenv, asig*kenv
endin
</CsInstruments>
<CsScore>
i 1 0 %.6f %.6f %.6f %.6f
e
</CsScore>
</CsoundSynthesizer>
`, duration(p), p.Motor.StartHz, p.Motor.EndHz, p.Motor.Gain)
}
func (p Project) CsoundMusic() string {
	var b strings.Builder
	b.WriteString(`<CsoundSynthesizer>
<CsOptions>
</CsOptions>
<CsInstruments>
sr = 48000
ksmps = 32
nchnls = 2
0dbfs = 1
instr 1
ifreq = cpsmidinn(p4)
asig oscili p5, ifreq, 1
kenv linseg 0, 0.02, 1, p3-0.05, 0.8, 0.03, 0
outs asig*kenv, asig*kenv
endin
</CsInstruments>
<CsScore>
`)
	for _, n := range p.Notes {
		fmt.Fprintf(&b, "i 1 %.6f %.6f %d %.6f\n", float64(n.StartTick)/PPQ*60/float64(p.BPM), float64(n.LengthTick)/PPQ*60/float64(p.BPM), n.Pitch, float64(n.Velocity)/127*0.09)
	}
	fmt.Fprintf(&b, "f 1 0 16384 10 1\nf 0 %.6f\ne\n</CsScore>\n</CsoundSynthesizer>\n", duration(p))
	return b.String()
}
func putVLQ(dst *bytes.Buffer, value uint32) {
	var arr [5]byte
	i := len(arr) - 1
	arr[i] = byte(value & 0x7f)
	for value >>= 7; value > 0; value >>= 7 {
		i--
		arr[i] = byte(value&0x7f) | 0x80
	}
	dst.Write(arr[i:])
}
func (p Project) MIDI() ([]byte, error) {
	if e := p.Validate(); e != nil {
		return nil, e
	}
	type event struct {
		tick     int
		priority int
		msg      []byte
	}
	ev := []event{{0, 0, []byte{0xFF, 0x51, 0x03, byte((60000000 / p.BPM) >> 16), byte((60000000 / p.BPM) >> 8), byte(60000000 / p.BPM)}}}
	for _, n := range p.Notes {
		ev = append(ev, event{n.StartTick, 2, []byte{0x90, byte(n.Pitch), byte(n.Velocity)}}, event{n.StartTick + n.LengthTick, 1, []byte{0x80, byte(n.Pitch), 0}})
	}
	sort.SliceStable(ev, func(i, j int) bool {
		if ev[i].tick != ev[j].tick {
			return ev[i].tick < ev[j].tick
		}
		return ev[i].priority < ev[j].priority
	})
	var tr bytes.Buffer
	prev := 0
	for _, e := range ev {
		putVLQ(&tr, uint32(e.tick-prev))
		tr.Write(e.msg)
		prev = e.tick
	}
	putVLQ(&tr, uint32(p.Beats*PPQ-prev))
	tr.Write([]byte{0xFF, 0x2F, 0})
	var out bytes.Buffer
	out.WriteString("MThd")
	binary.Write(&out, binary.BigEndian, uint32(6))
	binary.Write(&out, binary.BigEndian, uint16(0))
	binary.Write(&out, binary.BigEndian, uint16(1))
	binary.Write(&out, binary.BigEndian, uint16(PPQ))
	out.WriteString("MTrk")
	binary.Write(&out, binary.BigEndian, uint32(tr.Len()))
	out.Write(tr.Bytes())
	return out.Bytes(), nil
}
func parseVLQ(b []byte, i *int) (uint32, error) {
	var v uint32
	for j := 0; j < 4; j++ {
		if *i >= len(b) {
			return 0, io.ErrUnexpectedEOF
		}
		c := b[*i]
		*i += 1
		v = (v << 7) | uint32(c&0x7f)
		if c&0x80 == 0 {
			return v, nil
		}
	}
	return 0, errors.New("vlq too large")
}

// ImportMIDI deliberately accepts only the reproducible single-track, monophonic
// MIDI subset from MIDI(). External DAW exports can require an explicit adapter.
func ImportMIDI(p Project, b []byte) (Project, error) {
	if len(b) < 22 || string(b[:4]) != "MThd" || binary.BigEndian.Uint32(b[4:8]) != 6 || binary.BigEndian.Uint16(b[8:10]) != 0 || binary.BigEndian.Uint16(b[10:12]) != 1 || binary.BigEndian.Uint16(b[12:14]) != PPQ || string(b[14:18]) != "MTrk" || int(binary.BigEndian.Uint32(b[18:22])) != len(b)-22 {
		return p, errors.New("unsupported MIDI structure")
	}
	q := p
	q.Notes = nil
	idx := 22
	tick := 0
	active := -1
	vel := 0
	start := 0
	tempoFound := false
	ended := false
	for idx < len(b) {
		delta, e := parseVLQ(b, &idx)
		if e != nil {
			return p, e
		}
		tick += int(delta)
		if idx >= len(b) {
			return p, io.ErrUnexpectedEOF
		}
		status := b[idx]
		idx++
		switch status {
		case 0xFF:
			if idx >= len(b) {
				return p, io.ErrUnexpectedEOF
			}
			meta := b[idx]
			idx++
			sz, e := parseVLQ(b, &idx)
			if e != nil || idx+int(sz) > len(b) {
				return p, errors.New("invalid meta event")
			}
			if meta == 0x51 && sz == 3 {
				v := int(b[idx])<<16 | int(b[idx+1])<<8 | int(b[idx+2])
				if tempoFound || v != 60000000/p.BPM {
					return p, errors.New("tempo change unsupported")
				}
				tempoFound = true
			} else if meta == 0x2f && sz == 0 {
				ended = true
				if idx != len(b) {
					return p, errors.New("early EOT")
				}
			} else {
				return p, errors.New("unrecognized meta event")
			}
			idx += int(sz)
		case 0x90:
			if active >= 0 || idx+2 > len(b) {
				return p, errors.New("overlapping/short note on")
			}
			active = int(b[idx])
			vel = int(b[idx+1])
			idx += 2
			if vel == 0 {
				return p, errors.New("zero-velocity note on unsupported")
			}
			start = tick
		case 0x80:
			if idx+2 > len(b) || active != int(b[idx]) {
				return p, errors.New("unmatched note off")
			}
			idx += 2
			q.Notes = append(q.Notes, Note{Pitch: active, StartTick: start, LengthTick: tick - start, Velocity: vel})
			active = -1
		default:
			return p, fmt.Errorf("MIDI status 0x%x unsupported", status)
		}
	}
	if active >= 0 || !ended || !tempoFound {
		return p, errors.New("missing note off, tempo or end event")
	}
	if e := q.Validate(); e != nil {
		return p, e
	}
	return q, nil
}
func pitchInfo(n int) (step string, alter int, octave int) {
	steps := []string{"C", "C", "D", "D", "E", "F", "F", "G", "G", "A", "A", "B"}
	alterTable := []int{0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0}
	return steps[n%12], alterTable[n%12], n/12 - 1
}
func (p Project) MusicXML() ([]byte, error) {
	if e := p.Validate(); e != nil {
		return nil, e
	}
	// MusicXML accepts divisions/quarter beat. Every event and rest is preserved
	// at canonical 480 ticks; tuplets/ties are intentionally excluded from v1.
	typ := func(ticks int) string {
		switch ticks {
		case 120:
			return "16th"
		case 240:
			return "eighth"
		case 480:
			return "quarter"
		case 960:
			return "half"
		case 1920:
			return "whole"
		}
		return ""
	}
	var b strings.Builder
	b.WriteString("<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<!DOCTYPE score-partwise  PUBLIC \"-//Recordare//DTD MusicXML 4.0 Partwise//EN\" \"http://www.musicxml.org/dtds/partwise.dtd\">\n<score-partwise version=\"4.0\">\n<work><work-title>Original synthetic theme</work-title></work>\n<movement-title>Original synthetic theme</movement-title>\n<identification><creator type=\"composer\">Audio Foundry synthetic test fixture</creator></identification>\n<defaults/>\n<part-list><score-part id=\"P1\"><part-name>Melody</part-name><part-abbreviation>Mel.</part-abbreviation><score-instrument id=\"I1\"><instrument-name>Sine Lead</instrument-name></score-instrument><midi-instrument id=\"I1\"><midi-channel>1</midi-channel><midi-program>81</midi-program></midi-instrument></score-part></part-list>\n<part id=\"P1\">\n")
	next := 0
	for bar := 0; bar < p.Beats/4; bar++ {
		fmt.Fprintf(&b, "<measure number=\"%d\">\n", bar+1)
		if bar == 0 {
			fmt.Fprintf(&b, "<attributes><divisions>%d</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>\n<direction><direction-type><metronome><beat-unit>quarter</beat-unit><per-minute>%d</per-minute></metronome></direction-type><sound tempo=\"%d\" /></direction>\n", PPQ, p.BPM, p.BPM)
		}
		barEnd := (bar + 1) * 1920
		cursor := bar * 1920
		emitRest := func(ticks int) error {
			for ticks > 0 {
				amt := 1920
				for amt > ticks {
					amt /= 2
				}
				if amt < 120 {
					return errors.New("unrepresentable rest")
				}
				fmt.Fprintf(&b, "<note><rest/><duration>%d</duration><type>%s</type></note>\n", amt, typ(amt))
				ticks -= amt
			}
			return nil
		}
		for next < len(p.Notes) && p.Notes[next].StartTick < barEnd {
			n := p.Notes[next]
			if e := emitRest(n.StartTick - cursor); e != nil {
				return nil, e
			}
			step, alter, oct := pitchInfo(n.Pitch)
			t := typ(n.LengthTick)
			if t == "" {
				return nil, errors.New("duration not supported in MusicXML subset")
			}
			fmt.Fprintf(&b, "<note><pitch><step>%s</step><alter>%d</alter><octave>%d</octave></pitch><duration>%d</duration><type>%s</type></note>\n", step, alter, oct, n.LengthTick, t)
			cursor = n.StartTick + n.LengthTick
			next++
		}
		if e := emitRest(barEnd - cursor); e != nil {
			return nil, e
		}
		b.WriteString("</measure>\n")
	}
	b.WriteString("</part>\n</score-partwise>\n")
	return []byte(b.String()), nil
}
func (p Project) Export(dir string) error {
	if e := p.Validate(); e != nil {
		return e
	}
	if _, e := os.Lstat(dir); e == nil {
		return errors.New("export path exists; refusing overwrite")
	} else if !os.IsNotExist(e) {
		return e
	}
	if e := os.Mkdir(dir, 0700); e != nil {
		return e
	}
	data, _ := p.Bytes()
	midi, e := p.MIDI()
	if e != nil {
		return e
	}
	score, e := p.MusicXML()
	if e != nil {
		return e
	}
	files := map[string][]byte{"project.json": data, "mechanical_motor.csd": []byte(p.CsoundMotor()), "musical_theme.csd": []byte(p.CsoundMusic()), "melody.mid": midi, "melody.musicxml": score}
	for filename, payload := range files {
		if e := WriteNew(filepath.Join(dir, filename), payload); e != nil {
			return e
		}
	}
	return nil
}