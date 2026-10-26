// Command authorctl provides noninteractive, versioned edits of audio source
// recipes, procedural Csound programs and MusicXML/MIDI interchange.
package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"example.invalid/audio-editable"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"time"
)

func usage() error {
	return errors.New("usage: authorctl init -out NEW.json | edit -in OLD.json -out NEW.json -field FIELD -value VALUE | export -in PROJ.json -out NEW_DIR | import-midi -in PROJ.json -midi MIDI_FILE -out NEW.json | render -bundle EXPORTED_DIR -out NEW_DIR")
}
func run(args []string) error {
	if len(args) == 0 {
		return usage()
	}
	switch args[0] {
	case "init":
		f := flag.NewFlagSet("init", flag.ContinueOnError)
		out := f.String("out", "", "new JSON project")
		if e := f.Parse(args[1:]); e != nil {
			return e
		}
		if *out == "" || f.NArg() != 0 {
			return usage()
		}
		b, e := editable.Default().Bytes()
		if e != nil {
			return e
		}
		return editable.WriteNew(*out, b)
	case "edit":
		f := flag.NewFlagSet("edit", flag.ContinueOnError)
		input := f.String("in", "", "source project")
		out := f.String("out", "", "new project")
		field := f.String("field", "", "property")
		value := f.String("value", "", "value")
		if e := f.Parse(args[1:]); e != nil {
			return e
		}
		if *input == "" || *out == "" || *field == "" || *value == "" || f.NArg() != 0 {
			return usage()
		}
		p, e := editable.Read(*input)
		if e != nil {
			return e
		}
		q, e := editable.Change(p, *field, *value)
		if e != nil {
			return e
		}
		b, e := q.Bytes()
		if e != nil {
			return e
		}
		return editable.WriteNew(*out, b)
	case "import-midi":
		f := flag.NewFlagSet("import-midi", flag.ContinueOnError)
		input := f.String("in", "", "source project")
		mid := f.String("midi", "", "monophonic MIDI SMF0")
		out := f.String("out", "", "new project")
		if e := f.Parse(args[1:]); e != nil {
			return e
		}
		if *input == "" || *mid == "" || *out == "" || f.NArg() != 0 {
			return usage()
		}
		p, e := editable.Read(*input)
		if e != nil {
			return e
		}
		data, e := os.ReadFile(*mid)
		if e != nil {
			return e
		}
		q, e := editable.ImportMIDI(p, data)
		if e != nil {
			return e
		}
		b, e := q.Bytes()
		if e != nil {
			return e
		}
		return editable.WriteNew(*out, b)
	case "export":
		f := flag.NewFlagSet("export", flag.ContinueOnError)
		input := f.String("in", "", "source project")
		out := f.String("out", "", "new output bundle directory")
		if e := f.Parse(args[1:]); e != nil {
			return e
		}
		if *input == "" || *out == "" || f.NArg() != 0 {
			return usage()
		}
		p, e := editable.Read(*input)
		if e != nil {
			return e
		}
		return p.Export(*out)
	case "render":
		f := flag.NewFlagSet("render", flag.ContinueOnError)
		bundle := f.String("bundle", "", "existing exported source bundle")
		out := f.String("out", "", "new output directory")
		if e := f.Parse(args[1:]); e != nil {
			return e
		}
		if *bundle == "" || *out == "" || f.NArg() != 0 {
			return usage()
		}
		return render(*bundle, *out)
	default:
		return usage()
	}
}
func hash(path string) (string, int64, error) {
	f, e := os.Open(path)
	if e != nil {
		return "", 0, e
	}
	defer f.Close()
	h := sha256.New()
	n, e := io.Copy(h, f)
	return hex.EncodeToString(h.Sum(nil)), n, e
}
func render(bundle, out string) error {
	p, e := editable.Read(filepath.Join(bundle, "project.json"))
	if e != nil {
		return e
	}
	for _, entry := range []struct {
		name string
		want string
	}{{"mechanical_motor.csd", p.CsoundMotor()}, {"musical_theme.csd", p.CsoundMusic()}} {
		data, e := os.ReadFile(filepath.Join(bundle, entry.name))
		if e != nil {
			return e
		}
		if string(data) != entry.want {
			return errors.New("unreconciled native Csound edit: " + entry.name + "; edit canonical source and re-export")
		}
	}
	orig, e := p.MIDI()
	if e != nil {
		return e
	}
	seen, e := os.ReadFile(filepath.Join(bundle, "melody.mid"))
	if e != nil {
		return e
	}
	q, e := editable.ImportMIDI(p, seen)
	if e != nil {
		return e
	}
	_ = q
	if string(orig) != string(seen) {
		return errors.New("exported MIDI changed; reconcile through import-midi before render")
	}
	if _, e = os.Lstat(out); e == nil {
		return errors.New("output directory exists")
	} else if !os.IsNotExist(e) {
		return e
	}
	if e = os.Mkdir(out, 0700); e != nil {
		return e
	}
	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()
	results := make([]map[string]interface{}, 0, 2)
	specs := []string{"mechanical_motor", "musical_theme"}
	for _, s := range specs {
		dest := filepath.Join(out, s+".wav")
		cmd := exec.CommandContext(ctx, "csound", "-d", "-m0", "-W", "-s", "-o", dest, filepath.Join(bundle, s+".csd"))
		output, err := cmd.CombinedOutput()
		if err != nil {
			return fmt.Errorf("Csound %s: %w (%s)", s, err, string(output))
		}
		b, err := exec.CommandContext(ctx, "ffprobe", "-v", "error", "-show_entries", "stream=codec_name,sample_rate,channels:format=duration", "-of", "json", dest).Output()
		if err != nil {
			return err
		}
		var probe struct {
			Streams []struct {
				Codec      string `json:"codec_name"`
				SampleRate string `json:"sample_rate"`
				Channels   int    `json:"channels"`
			} `json:"streams"`
			Format struct {
				Duration string `json:"duration"`
			} `json:"format"`
		}
		if err = json.Unmarshal(b, &probe); err != nil {
			return err
		}
		if len(probe.Streams) != 1 || probe.Streams[0].Codec != "pcm_s16le" || probe.Streams[0].SampleRate != "48000" || probe.Streams[0].Channels != 2 {
			return errors.New("Csound output unexpected encoding")
		}
		duration, err := strconv.ParseFloat(probe.Format.Duration, 64)
		if err != nil || duration < float64(p.Beats)*60/float64(p.BPM)-0.01 || duration > float64(p.Beats)*60/float64(p.BPM)+0.01 {
			return errors.New("Csound stem truncated or length mismatch")
		}
		digest, size, err := hash(dest)
		if err != nil {
			return err
		}
		results = append(results, map[string]interface{}{"file": s + ".wav", "sha256": digest, "bytes": size, "duration_s": duration})
	}
	length := p.Beats * 60000 / p.BPM
	type track struct {
		ID         string  `json:"id"`
		Category   string  `json:"category"`
		Asset      string  `json:"asset"`
		SHA256     string  `json:"sha256"`
		StartMS    int     `json:"start_ms"`
		OffsetMS   int     `json:"offset_ms"`
		DurationMS int     `json:"duration_ms"`
		GainDB     float64 `json:"gain_db"`
		FadeInMS   int     `json:"fade_in_ms"`
		FadeOutMS  int     `json:"fade_out_ms"`
	}
	tracks := []track{}
	for i, s := range specs {
		cat := "mechanical"
		if i == 1 {
			cat = "music"
		}
		tracks = append(tracks, track{ID: s, Category: cat, Asset: s + ".wav", SHA256: results[i]["sha256"].(string), DurationMS: length})
	}
	m := map[string]interface{}{"schema": "scene_audio.v1", "id": "synthetic_editable_score", "classification": editable.Public, "duration_ms": length, "sample_rate_hz": 48000, "channels": 2, "tracks": tracks, "events": []interface{}{}}
	data, err := json.MarshalIndent(m, "", "  ")
	if err != nil {
		return err
	}
	if err = editable.WriteNew(filepath.Join(out, "scene_audio.json"), append(data, '\n')); err != nil {
		return err
	}
	rec := map[string]interface{}{"schema": "editable_audio.receipt.v1", "classification": editable.Public, "engine": "Csound", "sources": results, "source_project": "project.json", "music_midi": "melody.mid", "music_notation": "melody.musicxml", "authoring_project": "editable_audio.v1", "native_ardour_session_exported": false}
	rb, err := json.MarshalIndent(rec, "", "  ")
	if err != nil {
		return err
	}
	if err = editable.WriteNew(filepath.Join(out, "receipt.json"), append(rb, '\n')); err != nil {
		return err
	}
	fmt.Printf("editable_audio_render_PASS sources=%d stems=2\n", len(results))
	return nil
}
func main() {
	if e := run(os.Args[1:]); e != nil {
		fmt.Fprintln(os.Stderr, "AUTHORCTL_FIRST_FAILURE:", e)
		os.Exit(1)
	}
}