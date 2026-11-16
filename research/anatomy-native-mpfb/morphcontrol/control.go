// Package morphcontrol provides a deterministic, fail-closed, versioned
// three-mesh morph command planner. It is NOT a Godot transport nor a
// tissue/organ physical model. Data is only synthetic public MPFB metadata.
package morphcontrol

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"slices"
	"sync"
)

const Schema = "r048.morphcontrol.transaction.v1"

var (
	ErrInvalid = errors.New("morph control invalid proposal")
	ErrStale = errors.New("morph control stale revision")
	ErrTampered = errors.New("morph control plan digest mismatch")
)

var Channels = [8]string{
	"$md-$as-$fe-$yn", "$md-$as-$ma-$yn",
	"$md-$ca-$fe-$yn", "$md-$ca-$ma-$yn",
	"$md-$af-$fe-$yn", "$md-$af-$ma-$yn",
	"$md-universal-$fe-$yn-$av$mu-$av$wg",
	"$md-universal-$ma-$yn-$av$mu-$av$wg",
}

var Targets = [3]string{
	"R043_EditableMask_MPFB_Body",
	"R045_AnchorSynthetic_Left",
	"R045_AnchorSynthetic_Right",
}

// Entry is a single explicit runtime set_blend_shape_value command.
// A plan always contains 24 entries ordered by target then source morph index.
type Entry struct {
	Target string `json:"target"`
	Channel string `json:"channel"`
	Index int `json:"index"`
	Value float64 `json:"value"`
}

type Plan struct {
	Schema string `json:"schema"`
	ExpectedRevision uint64 `json:"expected_revision"`
	Sequence []Entry `json:"sequence"`
	SHA256 string `json:"sha256"`
}

type Receipt struct {
	Schema string `json:"schema"`
	Revision uint64 `json:"revision"`
	CommittedSHA256 string `json:"committed_sha256"`
	PreviousSHA256 string `json:"previous_sha256"`
	Commands int `json:"commands"`
	Status string `json:"status"`
}

type Snapshot struct {
	Revision uint64 `json:"revision"`
	Values [8]float64 `json:"values"`
	Digest string `json:"digest"`
}

type Controller struct {
	mu sync.Mutex
	revision uint64
	values [8]float64
	digest string
}

// New starts a zeroed synthetic scene with immutable starting receipt.
// No network/graphics IO, credentials or character assets.
func New() *Controller {
	const empty = "r048.empty.v1"
	hash := sha256.Sum256([]byte(empty))
	return &Controller{digest: hex.EncodeToString(hash[:])}
}

func (c *Controller) Snapshot() Snapshot {
	c.mu.Lock()
	defer c.mu.Unlock()
	return Snapshot{Revision:c.revision, Values:c.values, Digest:c.digest}
}

func validateValues(values map[string]float64) ([8]float64,error) {
	var out [8]float64
	if len(values) != len(Channels) {
		return out, fmt.Errorf("%w: require exactly eight source morphs",ErrInvalid)
	}
	for i,name := range Channels {
		v,ok := values[name]
		if !ok || math.IsNaN(v) || math.IsInf(v,0) || v < -1 || v > 1 {
			return out, fmt.Errorf("%w: missing, nonfinite or out-of-range %q",ErrInvalid,name)
		}
		if v == 0 {
			v = 0 // canonicalize negative zero
		}
		out[i] = v
	}
	return out,nil
}

func signature(p Plan) (string,error) {
	// Hash excludes SHA256 field itself, avoiding circularity and
	// ensuring source morph names/target ordering/values are protected.
	payload := struct {
		Schema string `json:"schema"`
		ExpectedRevision uint64 `json:"expected_revision"`
		Sequence []Entry `json:"sequence"`
	}{p.Schema,p.ExpectedRevision,p.Sequence}
	raw,err := json.Marshal(payload)
	if err != nil {return "",err}
	h := sha256.Sum256(raw)
	return hex.EncodeToString(h[:]),nil
}

func build(expected uint64, raw [8]float64) (Plan,error) {
	p:=Plan{Schema:Schema,ExpectedRevision:expected,
		Sequence:make([]Entry,0,len(Targets)*len(Channels))}
	for _,target:=range Targets {
		for i,name:=range Channels {
			p.Sequence=append(p.Sequence,Entry{Target:target,Channel:name,Index:i,Value:raw[i]})
		}
	}
	sig,err:=signature(p)
	if err!=nil {return Plan{},err}
	p.SHA256=sig
	return p,nil
}

// Prepare plans three target mesh updates and validates the expected
// generation. There is no mutation before a later successful Commit.
func (c *Controller) Prepare(expected uint64, values map[string]float64) (Plan,error) {
	raw,err:=validateValues(values)
	if err!=nil {return Plan{},err}
	c.mu.Lock()
	defer c.mu.Unlock()
	if expected!=c.revision {
		return Plan{},fmt.Errorf("%w: expected %d current %d",ErrStale,expected,c.revision)
	}
	return build(expected,raw)
}

// Commit never executes an external Godot command; it atomically records
// the verified plan that a separate checked adapter must apply. A user of
// this package must not claim real runtime update based on a receipt alone.
func (c *Controller) Commit(p Plan) (Receipt,error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if p.ExpectedRevision!=c.revision {
		return Receipt{},fmt.Errorf("%w: expected %d current %d",ErrStale,p.ExpectedRevision,c.revision)
	}
	if p.Schema!=Schema || len(p.Sequence)!=len(Targets)*len(Channels) {
		return Receipt{},fmt.Errorf("%w: wrong schema or command count",ErrInvalid)
	}
	values:=make(map[string]float64,len(Channels))
	for ti,target:=range Targets {
		for j,name:=range Channels {
			command:=p.Sequence[ti*len(Channels)+j]
			if command.Target!=target || command.Index!=j || command.Channel!=name {
				return Receipt{},fmt.Errorf("%w: invalid target or ordered morph index",ErrInvalid)
			}
			if ti==0 {values[name]=command.Value} else if command.Value!=values[name] {
				return Receipt{},fmt.Errorf("%w: target states diverge",ErrInvalid)
			}
		}
	}
	raw,err:=validateValues(values)
	if err!=nil {return Receipt{},err}
	expected,err:=build(c.revision,raw)
	if err!=nil {return Receipt{},err}
	if !slices.EqualFunc(p.Sequence,expected.Sequence,func(a,b Entry)bool{return a==b}) {
		return Receipt{},fmt.Errorf("%w: plan command mutation",ErrInvalid)
	}
	actualSig,err:=signature(p)
	if err!=nil {return Receipt{},err}
	if p.SHA256!=actualSig || p.SHA256!=expected.SHA256 {
		return Receipt{},ErrTampered
	}
	previous:=c.digest
	c.values=raw
	c.revision++
	// Chained digest includes both prior commit and verified new plan.
	chained:=sha256.Sum256([]byte(previous+":"+expected.SHA256))
	c.digest=hex.EncodeToString(chained[:])
	return Receipt{Schema:Schema,Revision:c.revision,
		CommittedSHA256:c.digest,PreviousSHA256:previous,
		Commands:len(expected.Sequence),Status:"PASS_NARROW_PREPARED_COMMANDS_ONLY"},nil
}
