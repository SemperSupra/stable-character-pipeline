// Package rendercontract defines a self-contained original public-safe
// synthetic rendering request. It is NOT Oneirifact's private canonical source,
// authorization fence, scene compiler, or real renderer.
package rendercontract

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"regexp"
	"slices"
	"strings"
)

const Schema = "synthetic.render-request/v0.1"
const Frame = "Z_UP_METERS_RIGHT_HANDED"
const Engine = "BLENDER_CYCLES_5_2_4_CPU"
const MaxSamplePixels uint64 = 100_000_000 // Static budget, not a runtime quota.

var namePattern = regexp.MustCompile(`^[A-Za-z][A-Za-z0-9_-]{0,63}$`)

type SourceBinding struct {
	DocumentID     string `json:"document_id"`
	Revision       string `json:"revision"`
	GraphSHA256    string `json:"graph_sha256"`
	InstanceSHA256 string `json:"instance_sha256,omitempty"`
}
type Object struct {
	ID           string     `json:"id"`
	FeaturePath  string     `json:"feature_path"`
	MaterialID   string     `json:"material_id"`
	Translation  [3]float64 `json:"translation"`
	UniformScale float64    `json:"uniform_scale"`
}
type Material struct {
	ID        string     `json:"id"`
	BaseColor [3]float64 `json:"base_color"`
	Metallic  float64    `json:"metallic"`
	Roughness float64    `json:"roughness"`
}
type Camera struct {
	ID         string     `json:"id"`
	Position   [3]float64 `json:"position"`
	Target     [3]float64 `json:"target"`
	Up         [3]float64 `json:"up"`
	FOVDegrees float64    `json:"fov_degrees"`
}
type Light struct {
	ID         string     `json:"id"`
	Type       string     `json:"type"`
	Position   [3]float64 `json:"position"`
	PowerWatts float64    `json:"power_watts"`
	SizeMeters float64    `json:"size_meters"`
}
type Options struct {
	Engine  string `json:"engine"`
	Width   int    `json:"width"`
	Height  int    `json:"height"`
	Samples int    `json:"samples"`
	Seed    uint32 `json:"seed"`
}
type Request struct {
	Schema    string        `json:"schema"`
	Source    SourceBinding `json:"source"`
	Frame     string        `json:"frame"`
	Objects   []Object      `json:"objects"`
	Materials []Material    `json:"materials"`
	Cameras   []Camera      `json:"cameras"`
	Lights    []Light       `json:"lights"`
	Options   Options       `json:"options"`
}

func finite(v float64) bool { return !math.IsNaN(v) && !math.IsInf(v, 0) }
func name(s string) bool { return namePattern.MatchString(s) }
func digest(s string) bool {
	if len(s) != 71 || !strings.HasPrefix(s, "sha256:") || s != strings.ToLower(s) { return false }
	_, err := hex.DecodeString(s[7:])
	return err == nil
}
func occurrencePath(s string) bool {
	if s == "" || len(s) > 512 || strings.ContainsRune(s, 92) { return false }
	for _, seg := range strings.Split(s, "/") {
		if !name(seg) { return false }
	}
	return true
}
func vecFinite(v [3]float64) bool { return finite(v[0]) && finite(v[1]) && finite(v[2]) }
func subtract(a, b [3]float64) [3]float64 {
	return [3]float64{a[0]-b[0], a[1]-b[1], a[2]-b[2]}
}
func normSq(v [3]float64) float64 { return v[0]*v[0]+v[1]*v[1]+v[2]*v[2] }
func cross(a,b [3]float64) [3]float64 {
	return [3]float64{a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]}
}

// Canonicalize validates/sorts a defensive copy. It cannot attest the
// referenced source's existence, object geometry, actor identity or consent.
func Canonicalize(in Request) (Request,error) {
	v:=in
	if v.Schema!=Schema || v.Frame!=Frame {return Request{},errors.New("unsupported schema/frame")}
	if !name(v.Source.DocumentID) || !name(v.Source.Revision) || !digest(v.Source.GraphSHA256) ||
		(v.Source.InstanceSHA256!="" && !digest(v.Source.InstanceSHA256)) {
		return Request{},errors.New("invalid immutable source reference")
	}
	if v.Options.Engine!=Engine || v.Options.Width<64 || v.Options.Width>2048 ||
		v.Options.Height<64 || v.Options.Height>2048 ||
		v.Options.Samples<1 || v.Options.Samples>256 {
		return Request{},errors.New("unsupported renderer/resolution/samples")
	}
	if uint64(v.Options.Width)*uint64(v.Options.Height)*uint64(v.Options.Samples)>MaxSamplePixels {
		return Request{},errors.New("static sample-pixel budget exceeded")
	}
	if len(v.Objects)<1 || len(v.Objects)>256 || len(v.Materials)<1 || len(v.Materials)>32 ||
		len(v.Cameras)<1 || len(v.Cameras)>16 || len(v.Lights)<1 || len(v.Lights)>32 {
		return Request{},errors.New("declaration count outside bounds")
	}
	v.Objects=slices.Clone(in.Objects)
	v.Materials=slices.Clone(in.Materials)
	v.Cameras=slices.Clone(in.Cameras)
	v.Lights=slices.Clone(in.Lights)
	slices.SortFunc(v.Objects,func(a,b Object)int{return strings.Compare(a.ID,b.ID)})
	slices.SortFunc(v.Materials,func(a,b Material)int{return strings.Compare(a.ID,b.ID)})
	slices.SortFunc(v.Cameras,func(a,b Camera)int{return strings.Compare(a.ID,b.ID)})
	slices.SortFunc(v.Lights,func(a,b Light)int{return strings.Compare(a.ID,b.ID)})
	materials:=map[string]bool{}
	for _,m:=range v.Materials{
		if !name(m.ID) || !finite(m.Metallic)||m.Metallic<0||m.Metallic>1||
		   !finite(m.Roughness)||m.Roughness<0||m.Roughness>1||!vecFinite(m.BaseColor){
			return Request{},fmt.Errorf("invalid material %q",m.ID)
		}
		for _,c:=range m.BaseColor {if c<0||c>1 {return Request{},fmt.Errorf("invalid material color %q",m.ID)}}
		if materials[m.ID] {return Request{},fmt.Errorf("duplicate material %q",m.ID)}
		materials[m.ID]=true
	}
	objects,paths:=map[string]bool{},map[string]bool{}
	for _,o:=range v.Objects{
		if !name(o.ID)||!occurrencePath(o.FeaturePath)||!materials[o.MaterialID]||
		   !vecFinite(o.Translation)||!finite(o.UniformScale)||o.UniformScale<=0||o.UniformScale>1000{
			return Request{},fmt.Errorf("invalid object %q",o.ID)
		}
		if objects[o.ID]||paths[o.FeaturePath]{return Request{},errors.New("duplicate object/occurrence identity")}
		objects[o.ID],paths[o.FeaturePath]=true,true
	}
	cameras:=map[string]bool{}
	for _,c:=range v.Cameras{
		if !name(c.ID)||!vecFinite(c.Position)||!vecFinite(c.Target)||!vecFinite(c.Up)||
		   !finite(c.FOVDegrees)||c.FOVDegrees<1||c.FOVDegrees>179 {
			return Request{},fmt.Errorf("invalid camera %q",c.ID)
		}
		direction:=subtract(c.Target,c.Position)
		if normSq(direction)<1e-12||normSq(c.Up)<1e-12||normSq(cross(direction,c.Up))<1e-12 ||
		   !finite(normSq(direction))||!finite(normSq(c.Up))||!finite(normSq(cross(direction,c.Up))){
			return Request{},fmt.Errorf("degenerate/unbounded camera %q",c.ID)
		}
		if cameras[c.ID]{return Request{},errors.New("duplicate camera")}
		cameras[c.ID]=true
	}
	lights:=map[string]bool{}
	for _,l:=range v.Lights {
		if !name(l.ID)||(l.Type!="POINT"&&l.Type!="AREA")||!vecFinite(l.Position)||
		   !finite(l.PowerWatts)||l.PowerWatts<0||l.PowerWatts>1e7||
		   !finite(l.SizeMeters)||l.SizeMeters<0||l.SizeMeters>1e4||
		   (l.Type=="AREA"&&l.SizeMeters<=0)||(l.Type=="POINT"&&l.SizeMeters!=0){
			return Request{},fmt.Errorf("invalid emitter %q",l.ID)
		}
		if lights[l.ID]{return Request{},errors.New("duplicate emitter")}
		lights[l.ID]=true
	}
	return v,nil
}
// Fingerprint is a validated deterministic synthetic job digest, not an
// authenticated source/renderer result.
func Fingerprint(in Request)(string,error){
	v,err:=Canonicalize(in);if err!=nil{return "",err}
	data,err:=json.Marshal(v);if err!=nil{return "",err}
	sum:=sha256.Sum256(data)
	return "sha256:"+hex.EncodeToString(sum[:]),nil
}
