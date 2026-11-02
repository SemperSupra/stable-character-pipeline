// Package bvh qualifies a bounded self-authored BVH hierarchical motion file.
// Output is original joint FK in explicitly declared meters per unit. A native
// source, subject, identity, rights, renderer and species are NEVER inferred.
package bvh

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"math"
	"math/big"
	"strconv"
	"strings"
)

const MaxBytes = 2 << 20
const MaxJoints = 256
const MaxFrames = 5000
const MaxChannels = 1024

type Vec3 [3]float64
type Joint struct {
	Name     string   `json:"name"`
	Parent   int      `json:"parent"`
	Offset   Vec3     `json:"offset_source_units"`
	Channels []string `json:"channels"`
}
type Motion struct {
	Rights           string      `json:"rights"`
	SourceSHA256     string      `json:"source_sha256"`
	Joints           []Joint     `json:"joints"`
	FrameTimeSeconds string      `json:"frame_time_seconds"`
	Frames           [][]float64 `json:"-"`
	MeterPerUnit     float64     `json:"meters_per_unit"`
}
type WorldJoint struct {
	Name           string `json:"name"`
	PositionMeters Vec3   `json:"position_meters"`
}

func finite(v float64) bool { return !math.IsNaN(v) && !math.IsInf(v, 0) }
func nameSafe(s string) bool {
	if len(s) < 1 || len(s) > 100 {
		return false
	}
	for _, r := range s {
		if !(r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' || r >= '0' && r <= '9' || r == '_' || r == '-' || r == '.') {
			return false
		}
	}
	return true
}
func numeric(s string) (float64, error) {
	f, e := strconv.ParseFloat(s, 64)
	if e != nil || !finite(f) {
		return 0, errors.New("nonfinite or invalid numeric field")
	}
	return f, nil
}
func vec3(x, y, z float64) Vec3    { return Vec3{x, y, z} }
func add(a, b Vec3) Vec3           { return Vec3{a[0] + b[0], a[1] + b[1], a[2] + b[2]} }
func scale(a Vec3, k float64) Vec3 { return Vec3{a[0] * k, a[1] * k, a[2] * k} }

type Mat3 [3][3]float64

func identity() Mat3 { return Mat3{{1, 0, 0}, {0, 1, 0}, {0, 0, 1}} }
func mul(a, b Mat3) Mat3 {
	var out Mat3
	for i := 0; i < 3; i++ {
		for j := 0; j < 3; j++ {
			for k := 0; k < 3; k++ {
				out[i][j] += a[i][k] * b[k][j]
			}
		}
	}
	return out
}
func rotate(a Mat3, v Vec3) Vec3 {
	return Vec3{a[0][0]*v[0] + a[0][1]*v[1] + a[0][2]*v[2], a[1][0]*v[0] + a[1][1]*v[1] + a[1][2]*v[2], a[2][0]*v[0] + a[2][1]*v[1] + a[2][2]*v[2]}
}
func axisRotation(axis byte, radians float64) Mat3 {
	c, s := math.Cos(radians), math.Sin(radians)
	switch axis {
	case 'X':
		return Mat3{{1, 0, 0}, {0, c, -s}, {0, s, c}}
	case 'Y':
		return Mat3{{c, 0, s}, {0, 1, 0}, {-s, 0, c}}
	case 'Z':
		return Mat3{{c, -s, 0}, {s, c, 0}, {0, 0, 1}}
	}
	panic("validated axis")
}
func tokens(src string) []string {
	src = strings.ReplaceAll(src, "{", " { ")
	src = strings.ReplaceAll(src, "}", " } ")
	return strings.Fields(src)
}

type parser struct {
	tokens        []string
	pos           int
	joints        []Joint
	totalChannels int
}

func (p *parser) next() (string, error) {
	if p.pos >= len(p.tokens) {
		return "", errors.New("unexpected end of BVH")
	}
	s := p.tokens[p.pos]
	p.pos++
	return s, nil
}
func (p *parser) expect(x string) error {
	got, e := p.next()
	if e != nil {
		return e
	}
	if got != x {
		return fmt.Errorf("expected %q, got %q", x, got)
	}
	return nil
}
func (p *parser) joint(parent int, kind string) error {
	if kind != "ROOT" && kind != "JOINT" {
		return errors.New("unsupported joint kind")
	}
	name, e := p.next()
	if e != nil || !nameSafe(name) {
		return errors.New("bad joint name")
	}
	if len(p.joints) >= MaxJoints {
		return errors.New("too many joints")
	}
	for _, j := range p.joints {
		if j.Name == name {
			return errors.New("duplicate joint name")
		}
	}
	if e = p.expect("{"); e != nil {
		return e
	}
	if e = p.expect("OFFSET"); e != nil {
		return e
	}
	var offset Vec3
	for i := 0; i < 3; i++ {
		s, err := p.next()
		if err != nil {
			return err
		}
		offset[i], err = numeric(s)
		if err != nil {
			return err
		}
	}
	if e = p.expect("CHANNELS"); e != nil {
		return e
	}
	nstr, e := p.next()
	if e != nil {
		return e
	}
	n, e := strconv.Atoi(nstr)
	if e != nil || n < 3 || n > 6 {
		return errors.New("unsupported channel count")
	}
	idx := len(p.joints)
	j := Joint{Name: name, Parent: parent, Offset: offset}
	seen := map[string]bool{}
	rotations := 0
	positions := 0
	for i := 0; i < n; i++ {
		ch, err := p.next()
		if err != nil {
			return err
		}
		switch ch {
		case "Xrotation", "Yrotation", "Zrotation":
			rotations++
		case "Xposition", "Yposition", "Zposition":
			positions++
		default:
			return errors.New("unknown BVH channel")
		}
		if seen[ch] {
			return errors.New("duplicate BVH channel")
		}
		seen[ch] = true
		j.Channels = append(j.Channels, ch)
	}
	if rotations != 3 || !(positions == 0 && n == 3 || parent < 0 && positions == 3 && n == 6) {
		return errors.New("unsupported BVH hierarchy joint DOF")
	}
	p.totalChannels += n
	if p.totalChannels > MaxChannels {
		return errors.New("too many channels")
	}
	p.joints = append(p.joints, j)
	for {
		kind, err := p.next()
		if err != nil {
			return err
		}
		switch kind {
		case "JOINT":
			if e = p.joint(idx, kind); e != nil {
				return e
			}
		case "End":
			if e = p.expect("Site"); e != nil {
				return e
			}
			if e = p.expect("{"); e != nil {
				return e
			}
			if e = p.expect("OFFSET"); e != nil {
				return e
			}
			for k := 0; k < 3; k++ {
				s, er := p.next()
				if er != nil {
					return er
				}
				if _, er = numeric(s); er != nil {
					return er
				}
			}
			if e = p.expect("}"); e != nil {
				return e
			}
		case "}":
			return nil
		default:
			return fmt.Errorf("unexpected hierarchy token %q", kind)
		}
	}
}

// Parse accepts only an explicitly self-authored fixture. It does not infer
// rights by filename, input content, or a claimed label from third-party data.
func Parse(src []byte, rights string, metersPerUnit float64) (*Motion, error) {
	if rights != "ORIGINAL_SELF_AUTHORED_SYNTHETIC" {
		return nil, errors.New("BVH_RIGHTS_NOT_ADMITTED")
	}
	if len(src) == 0 || len(src) > MaxBytes || !finite(metersPerUnit) || metersPerUnit <= 0 || metersPerUnit > 100 {
		return nil, errors.New("bad source size or explicit unit")
	}
	p := &parser{tokens: tokens(string(src))}
	if e := p.expect("HIERARCHY"); e != nil {
		return nil, e
	}
	if e := p.expect("ROOT"); e != nil {
		return nil, e
	}
	if e := p.joint(-1, "ROOT"); e != nil {
		return nil, e
	}
	if e := p.expect("MOTION"); e != nil {
		return nil, e
	}
	if e := p.expect("Frames:"); e != nil {
		return nil, e
	}
	cnt, e := p.next()
	if e != nil {
		return nil, e
	}
	n, e := strconv.Atoi(cnt)
	if e != nil || n < 2 || n > MaxFrames {
		return nil, errors.New("invalid frame budget")
	}
	if e = p.expect("Frame"); e != nil {
		return nil, e
	}
	if e = p.expect("Time:"); e != nil {
		return nil, e
	}
	time, e := p.next()
	if e != nil {
		return nil, e
	}
	rat, ok := new(big.Rat).SetString(time)
	if !ok || rat.Sign() <= 0 {
		return nil, errors.New("invalid frame time")
	}
	t, _ := rat.Float64()
	if !finite(t) || t < 1.0/500 || t > 1 {
		return nil, errors.New("frame time out of bounds")
	}
	if len(p.tokens)-p.pos != n*p.totalChannels {
		return nil, errors.New("frame/channel matrix size mismatch")
	}
	frames := make([][]float64, n)
	for i := 0; i < n; i++ {
		frames[i] = make([]float64, p.totalChannels)
		for j := 0; j < p.totalChannels; j++ {
			s, err := p.next()
			if err != nil {
				return nil, err
			}
			frames[i][j], err = numeric(s)
			if err != nil {
				return nil, err
			}
		}
	}
	h := sha256.Sum256(src)
	return &Motion{Rights: rights, SourceSHA256: hex.EncodeToString(h[:]), Joints: p.joints, FrameTimeSeconds: rat.RatString(), Frames: frames, MeterPerUnit: metersPerUnit}, nil
}

// Evaluate preserves the BVH channel order; no overclaim of species, source
// calibration, mocap quality or retargeted target semantics.
func (m *Motion) Evaluate(frame int) ([]WorldJoint, error) {
	if frame < 0 || frame >= len(m.Frames) {
		return nil, errors.New("frame index out of bounds")
	}
	if len(m.Joints) == 0 || !finite(m.MeterPerUnit) || m.MeterPerUnit <= 0 {
		return nil, errors.New("invalid motion")
	}
	result := make([]WorldJoint, len(m.Joints))
	orientations := make([]Mat3, len(m.Joints))
	cursor := 0
	for idx, j := range m.Joints {
		localR := identity()
		translation := j.Offset
		for _, ch := range j.Channels {
			v := m.Frames[frame][cursor]
			cursor++
			if !finite(v) {
				return nil, errors.New("nonfinite channel")
			}
			if strings.HasSuffix(ch, "position") {
				switch ch[0] {
				case 'X':
					translation[0] += v
				case 'Y':
					translation[1] += v
				case 'Z':
					translation[2] += v
				}
			} else {
				localR = mul(localR, axisRotation(ch[0], v*math.Pi/180))
			}
		}
		if idx == 0 {
			result[idx] = WorldJoint{j.Name, scale(translation, m.MeterPerUnit)}
			orientations[idx] = localR
		} else {
			parent := j.Parent
			if parent < 0 || parent >= idx {
				return nil, errors.New("invalid hierarchy order")
			}
			delta := rotate(orientations[parent], scale(translation, m.MeterPerUnit))
			result[idx] = WorldJoint{j.Name, add(result[parent].PositionMeters, delta)}
			orientations[idx] = mul(orientations[parent], localR)
		}
	}
	return result, nil
}
