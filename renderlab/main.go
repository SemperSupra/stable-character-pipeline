// renderlab is a source-safe, stdlib-only verification harness.
// It evaluates evidence consistency, NOT human preference or photorealism.
package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"image"
	_ "image/png"
	"io"
	"math"
	"os"
	"path/filepath"
	"regexp"
)

const schema = "renderlab.synthetic.v1"

var digestRE = regexp.MustCompile("^[a-f0-9]{64}$")

type Artifact struct {
	File   string `json:"file"`
	SHA256 string `json:"sha256"`
}

type Receipt struct {
	SchemaVersion    string   `json:"schema_version"`
	ExperimentID     string   `json:"experiment_id"`
	SceneID          string   `json:"scene_id"`
	SourceSHA256     string   `json:"source_sha256"`
	GeometrySHA256   string   `json:"geometry_sha256"`
	CameraSHA256     string   `json:"camera_sha256"`
	AnimationSHA256  string   `json:"animation_sha256"`
	Arm              string   `json:"arm"`
	Seed             int      `json:"seed"`
	Rights           string   `json:"rights"`
	Status           string   `json:"status"`
	Engine           string   `json:"engine"`
	Samples          int      `json:"samples"`
	Resolution       int      `json:"resolution"`
	ElapsedSeconds   float64  `json:"elapsed_seconds"`
	BeautyPNG        Artifact `json:"beauty_png"`
	RenderPassesEXR  Artifact `json:"render_passes_exr"`
}

type Comparison struct {
	SchemaVersion       string  `json:"schema_version"`
	Status              string  `json:"status"`
	SceneID             string  `json:"scene_id"`
	SourceSHA256        string  `json:"source_sha256"`
	BaselineReceiptHash string  `json:"baseline_receipt_sha256"`
	MaterialReceiptHash string  `json:"material_receipt_sha256"`
	ChangedPixelFraction float64 `json:"changed_pixel_fraction"`
	MeanAbsoluteRGBDelta float64 `json:"mean_absolute_rgb_delta"`
	BaselineSeconds     float64 `json:"baseline_elapsed_seconds"`
	MaterialSeconds     float64 `json:"material_elapsed_seconds"`
	Qualification      string  `json:"qualification"`
}

func walkJSON(dec *json.Decoder) error {
	t, err := dec.Token()
	if err != nil { return err }
	delim, ok := t.(json.Delim)
	if !ok { return nil }
	switch delim {
	case '{':
		keys := make(map[string]bool)
		for dec.More() {
			k, err := dec.Token()
			if err != nil { return err }
			s, ok := k.(string)
			if !ok { return errors.New("object key is not string") }
			if keys[s] { return fmt.Errorf("duplicate JSON key %q", s) }
			keys[s] = true
			if err := walkJSON(dec); err != nil { return err }
		}
		end, err := dec.Token()
		if err != nil || end != json.Delim('}') { return errors.New("invalid JSON object closing") }
	case '[':
		for dec.More() {
			if err := walkJSON(dec); err != nil { return err }
		}
		end, err := dec.Token()
		if err != nil || end != json.Delim(']') { return errors.New("invalid JSON array closing") }
	default:
		return errors.New("unexpected JSON delimiter")
	}
	return nil
}

func decodeStrict(b []byte, v any) error {
	if len(b) == 0 || len(b) > 1<<20 { return errors.New("missing or oversized receipt") }
	d := json.NewDecoder(bytes.NewReader(b))
	if err := walkJSON(d); err != nil { return err }
	if _, err := d.Token(); err != io.EOF { return errors.New("trailing JSON content") }
	d = json.NewDecoder(bytes.NewReader(b))
	d.DisallowUnknownFields()
	if err := d.Decode(v); err != nil { return err }
	return nil
}

func digest(b []byte) string {
	v := sha256.Sum256(b)
	return hex.EncodeToString(v[:])
}

func checkedArtifact(dir string, a Artifact, exr bool) ([]byte, error) {
	if a.File == "" || a.File != filepath.Base(a.File) || a.File == "." || a.File == ".." {
		return nil, errors.New("artifact filename must be a basename")
	}
	if !digestRE.MatchString(a.SHA256) { return nil, errors.New("invalid artifact digest") }
	p := filepath.Join(dir, a.File)
	fi, err := os.Lstat(p)
	if err != nil { return nil, err }
	if !fi.Mode().IsRegular() || fi.Size() < 10 || fi.Size() > 32<<20 { return nil, errors.New("artifact not an approved regular file") }
	b, err := os.ReadFile(p)
	if err != nil { return nil, err }
	if digest(b) != a.SHA256 { return nil, errors.New("artifact SHA256 mismatch") }
	if exr {
		if !bytes.HasPrefix(b, []byte{0x76, 0x2f, 0x31, 0x01}) { return nil, errors.New("not an OpenEXR payload") }
	}
	return b, nil
}

func inspectPNG(b []byte, resolution int) ([]uint8, int, error) {
	im, fmtName, err := image.Decode(bytes.NewReader(b))
	if err != nil || fmtName != "png" { return nil, 0, errors.New("cannot decode PNG") }
	bounds := im.Bounds()
	if bounds.Dx() != resolution || bounds.Dy() != resolution { return nil, 0, errors.New("unexpected image dimensions") }
	pixels := make([]uint8, 0, resolution*resolution*3)
	colors := make(map[[3]uint8]bool)
	for y := bounds.Min.Y; y < bounds.Max.Y; y++ {
		for x := bounds.Min.X; x < bounds.Max.X; x++ {
			r,g,b,_ := im.At(x,y).RGBA()
			v := [3]uint8{uint8(r>>8), uint8(g>>8), uint8(b>>8)}
			pixels = append(pixels, v[:]...)
			colors[v] = true
		}
	}
	if len(colors) < 12 { return nil, 0, errors.New("blank or low-diversity render") }
	return pixels, len(colors), nil
}

func loadReceipt(path string) (Receipt, []byte, []uint8, error) {
	var r Receipt
	b, err := os.ReadFile(path)
	if err != nil { return r, nil, nil, err }
	if err := decodeStrict(b,&r); err != nil { return r,nil,nil,err }
	if r.SchemaVersion != schema || r.ExperimentID != "r037-synthetic-material-screen" ||
		r.SceneID != "original-synthetic-head-v1" || r.Rights != "ORIGINAL_SYNTHETIC" ||
		r.Status != "PASS_RENDER_ONLY" || r.Engine != "CYCLES" {
		return r,nil,nil,errors.New("unadmitted schema, source, rights or status")
	}
	for _, h := range []string{r.SourceSHA256,r.GeometrySHA256,r.CameraSHA256,r.AnimationSHA256} {
		if !digestRE.MatchString(h) { return r,nil,nil,errors.New("invalid source/scene digest") }
	}
	if r.Arm != "baseline" && r.Arm != "physical_material" { return r,nil,nil,errors.New("invalid treatment") }
	if r.Seed != 13 || r.Samples < 4 || r.Samples > 128 || r.Resolution < 64 || r.Resolution > 1024 {
		return r,nil,nil,errors.New("unadmitted seed, samples or resolution")
	}
	if math.IsNaN(r.ElapsedSeconds) || math.IsInf(r.ElapsedSeconds,0) || r.ElapsedSeconds <= 0 || r.ElapsedSeconds > 3600 {
		return r,nil,nil,errors.New("invalid elapsed time")
	}
	dir := filepath.Dir(path)
	pngBytes, err := checkedArtifact(dir,r.BeautyPNG,false)
	if err != nil { return r,nil,nil,fmt.Errorf("beauty: %w",err) }
	_, err = checkedArtifact(dir,r.RenderPassesEXR,true)
	if err != nil { return r,nil,nil,fmt.Errorf("render passes: %w",err) }
	pixels, _, err := inspectPNG(pngBytes,r.Resolution)
	if err != nil { return r,nil,nil,err }
	return r,b,pixels,nil
}

func compare(leftPath,rightPath string) (Comparison,error) {
	a, ab, ap, err := loadReceipt(leftPath)
	if err != nil { return Comparison{},fmt.Errorf("baseline: %w",err) }
	b, bb, bp, err := loadReceipt(rightPath)
	if err != nil { return Comparison{},fmt.Errorf("material: %w",err) }
	if a.Arm != "baseline" || b.Arm != "physical_material" { return Comparison{}, errors.New("treatment labels/order mismatch") }
	if a.SceneID != b.SceneID || a.SourceSHA256 != b.SourceSHA256 ||
		a.GeometrySHA256 != b.GeometrySHA256 || a.CameraSHA256 != b.CameraSHA256 ||
		a.AnimationSHA256 != b.AnimationSHA256 || a.Seed != b.Seed ||
		a.Samples != b.Samples || a.Resolution != b.Resolution {
		return Comparison{},errors.New("unmatched source, mesh, camera, animation or rendering settings")
	}
	var changed, accum int64
	for i:=0;i<len(ap);i+=3 {
		var pixelChanged bool
		for c:=0;c<3;c++ {
			d:=int(ap[i+c])-int(bp[i+c])
			if d<0 { d = -d }
			accum+=int64(d)
			if d>2 { pixelChanged=true }
		}
		if pixelChanged { changed++ }
	}
	total := int64(len(ap)/3)
	frac := float64(changed)/float64(total)
	if frac<0.001 { return Comparison{}, errors.New("treatments are visually indistinguishable") }
	return Comparison{
		SchemaVersion:schema,
		Status:"PASS_STRUCTURAL_RENDER_DIFFERENCE_ONLY",
		SceneID:a.SceneID,SourceSHA256:a.SourceSHA256,
		BaselineReceiptHash:digest(ab),MaterialReceiptHash:digest(bb),
		ChangedPixelFraction:frac, MeanAbsoluteRGBDelta:float64(accum)/float64(len(ap)*255),
		BaselineSeconds:a.ElapsedSeconds,MaterialSeconds:b.ElapsedSeconds,
		Qualification:"NOT_PHOTOREALISM_OR_HUMAN_PREFERENCE_EVIDENCE",
	},nil
}

func run(args []string) error {
	fs:=flag.NewFlagSet("renderlab",flag.ContinueOnError)
	left:=fs.String("baseline","","baseline receipt JSON")
	right:=fs.String("material","","material receipt JSON")
	output:=fs.String("out","","output comparison JSON")
	if err:=fs.Parse(args);err!=nil{return err}
	if fs.NArg()!=0 || *left=="" || *right=="" || *output=="" {return errors.New("usage: renderlab -baseline file -material file -out report.json")}
	c,err:=compare(*left,*right)
	if err!=nil{return err}
	b,err:=json.MarshalIndent(c,"","  ")
	if err!=nil{return err}
	b=append(b,'
')
	if err:=os.WriteFile(*output,b,0644);err!=nil{return err}
	fmt.Print(string(b))
	return nil
}
func main() {
	if err:=run(os.Args[1:]);err!=nil{fmt.Fprintln(os.Stderr,"HOLD:",err);os.Exit(1)}
}
