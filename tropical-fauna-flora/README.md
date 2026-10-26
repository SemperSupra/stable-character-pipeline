# Tropical Fauna & Flora — standalone 3D modeling workcell

**Status:** public, original-source, deterministic **technical blockout**. Not a scientific ecosystem model, photoreal art, anatomically valid wildlife rig, or completed project.

This experiment models a field with two stylized buffalo, four egret proxies, tropical banana and coconut palms, grass, muddy ground and a shallow irrigation channel. Original procedural geometry is produced by a standalone Go program (Go standard library only), with rigid-part keyframe animation. The optional CPU rendering adapter reads **the exported glTF** and creates a preview movie with VTK and FFmpeg. No AI-generated concept imagery, identity data, licensed people models, vendor asset files, credentials, or connections to private workcells are included.

This is intentionally **independent of all human-character modeling, datasets, and animation**. No human-person code paths, assets or cross-repository imports are present. Future integration is out of scope.

## Local execution

Run from this workcell directory:

```bash
go test -count=1 ./...
go test -race -count=1 ./...
go vet ./...
go run . -config scene.json -out out
# Python 3.11, NumPy and VTK 9.x; FFmpeg available on PATH
python render_vtk.py --scene out/tropical_scene.gltf --out out --frames 96 --fps 12 --width 640 --height 360
ffmpeg -hide_banner -loglevel error -y -framerate 12 -i out/frame_%04d.png -c:v libx264 -pix_fmt yuv420p -movflags +faststart out/tropical_scene_v0.mp4
ffprobe -v error -show_entries format=duration:stream=nb_frames,width,height,r_frame_rate -of json out/tropical_scene_v0.mp4
```

The `out/` folder is excluded from version control. Source and scene inputs are declarative, bounded and versioned; outputs are not pre-computed. `scene.json` is the only source of positions, species counts, seed, duration, and grass density. A fixed seed and exact Go implementation reproduce byte-for-byte identical 3D assets. Run `go test -race` on a non-Windows supported runner with the race toolchain installed.

## Public GitHub Actions

Workflow: [`.github/workflows/tropical-fauna-flora.yml`](../.github/workflows/tropical-fauna-flora.yml) (repository root). It runs on PR modifications to this workcell and on matching `main` pushes, plus explicit manual dispatch. The job uses public GitHub-hosted Linux CPU resources and explicitly limits time, frames, resolution, and retention. It tests Go, builds the model, renders an MP4 and frame contact sheet, verifies the output, and uploads only derived simulation products and JSON receipts. No private Actions workflows or runners are invoked. No repository secrets are requested; checkout does not preserve credentials. For a public repo, standard GitHub-hosted runner minutes are not billed, subject to GitHub policy and service limits.

## Validation and nonclaims

- The animals are **stylized mechanical proxies** with rigid-segment animation; no skinning, anatomically correct bones, ground contact IK, or locomotion metrics.
- Tropical plants have procedural branches/leaves, but no validated botanical growth model, plant physiology or dynamic grass.
- Forage, collisions, grazing, water dynamics and ecosystem feedback are not implemented. All imagery from the earlier concept art is separate from model evidence.
- Vertex/material provenance is `main.go` in this workcell; no downloaded mesh or reference material is required.
- No source license has been selected for this workcell; publication is not a grant of open-source reuse rights. Select and document license before external distribution beyond viewing and testing in the authorized repository.

## Three audiences

- **Human:** read this document, edit `scene.json`, inspect `out/preview_4frame.png` and `out/tropical_scene_v0.mp4` artifact output.
- **Automation:** run the commands above and parse `out/receipt.json` with hashes, count and status.
- **Agent:** use the same declarative manifest, Go test suite, deterministic output and error boundaries. No hidden agent-specific mutating API.

Next: independently version each species asset, add a provider registry and source admission, qualify actual quadruped/egret rigs and footfall, integrate plant structures and forage interactions, verify rendering across environments, and only then consider a separately authorized integration with humans.
