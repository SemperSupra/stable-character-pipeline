// Command synthetic-scene emits an original public-only request to exercise
// the standalone rendercontract and a source-free Blender donor adapter.
// It does not read, import, expose or validate Oneirifact private graph source.
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"

	rendercontract "example.org/synthetic/rendercontract"
)

func makeRequest(variant string) rendercontract.Request {
	h := "sha256:" + strings.Repeat("a", 64) // Synthetic placeholder; NOT attested graph content.
	r := rendercontract.Request{
		Schema: rendercontract.Schema,
		Frame:  rendercontract.Frame,
		Source: rendercontract.SourceBinding{DocumentID: "OriginalSynthetic", Revision: "syntheticRevision1", GraphSHA256: h},
		Objects: []rendercontract.Object{
			{ID: "cube", FeaturePath: "root/cube", MaterialID: "blue", Translation: [3]float64{-0.8, 0, 0.7}, UniformScale: 1},
			{ID: "sphere", FeaturePath: "root/sphere", MaterialID: "red", Translation: [3]float64{0.9, 0, 0.85}, UniformScale: 1},
		},
		Materials: []rendercontract.Material{
			{ID: "blue", BaseColor: [3]float64{0.08, 0.25, 0.7}, Metallic: 0, Roughness: 0.34},
			{ID: "red", BaseColor: [3]float64{0.75, 0.18, 0.12}, Metallic: 0, Roughness: 0.22},
		},
		Cameras: []rendercontract.Camera{
			{ID: "camera", Position: [3]float64{5, -7, 4}, Target: [3]float64{0, 0, 0.8}, Up: [3]float64{0, 0, 1}, FOVDegrees: 45},
		},
		Lights: []rendercontract.Light{
			{ID: "area", Type: "AREA", Position: [3]float64{1, -3, 6}, PowerWatts: 1000, SizeMeters: 5},
		},
		Options: rendercontract.Options{Engine: rendercontract.Engine, Width: 320, Height: 240, Samples: 32, Seed: 139},
	}
	if variant == "B" || variant == "material" {
		r.Materials[0].BaseColor = [3]float64{0.07, 0.68, 0.24}
		r.Materials[1].BaseColor = [3]float64{0.18, 0.25, 0.79}
	}
	if variant == "B" || variant == "camera" {
		r.Cameras[0].Position = [3]float64{4, -6, 4.5}
	}
	if variant == "B" || variant == "light" {
		r.Lights[0].PowerWatts = 700
	}
	return r
}

func main() {
	variant := "A"
	if len(os.Args) > 2 {
		fmt.Fprintln(os.Stderr, "expected zero or one --variant=A|B|camera|material|light option")
		os.Exit(2)
	}
	if len(os.Args) == 2 {
		switch os.Args[1] {
		case "--variant=A":
			variant = "A"
		case "--variant=B":
			variant = "B"
		case "--variant=camera":
			variant = "camera"
		case "--variant=material":
			variant = "material"
		case "--variant=light":
			variant = "light"
		default:
			fmt.Fprintln(os.Stderr, "unknown variant")
			os.Exit(2)
		}
	}
	v, err := rendercontract.Canonicalize(makeRequest(variant))
	if err != nil {
		fmt.Fprintln(os.Stderr, "synthetic request invalid:", err)
		os.Exit(1)
	}
	digest, err := rendercontract.Fingerprint(v)
	if err != nil {
		fmt.Fprintln(os.Stderr, "synthetic fingerprint invalid:", err)
		os.Exit(1)
	}
	packet := map[string]any{
		"schema": "synthetic.cycles-scene-packet/v0.1",
		"variant": variant,
		"request": v,
		"synthetic_request_fingerprint": digest,
		"source_fidelity": "UNVERIFIED_SYNTHETIC_GEOMETRY_REGISTRY",
	}
	if err := json.NewEncoder(os.Stdout).Encode(packet); err != nil {
		fmt.Fprintln(os.Stderr, "encode packet:", err)
		os.Exit(1)
	}
}
