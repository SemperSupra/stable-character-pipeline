// Package attenuation implements a narrowly scoped, explicitly opt-in
// pressure-amplitude gain layer. It is not a room, Doppler, or HRTF model.
package attenuation

import (
    "errors"
    "math"
)
type Curve string
const (
    Identity Curve = "identity"
    InverseDistance Curve = "inverse_distance"
)
var ErrInput = errors.New("spatial attenuation: invalid source, gain, frame or distance")

type Envelope struct {
    Curve Curve
    ReferenceMeters float64
    MinimumMeters float64
}
func finite(x float64) bool { return !math.IsInf(x, 0) && !math.IsNaN(x) }
func (e Envelope) Validate() error {
    if !finite(e.ReferenceMeters) || !finite(e.MinimumMeters) || e.ReferenceMeters<=0 || e.MinimumMeters<=0 ||
       (e.Curve != Identity && e.Curve != InverseDistance) {
        return ErrInput
    }
    return nil
}
// Gain returns the pressure-like amplitude multiplier clamped to [0,1].
// This expresses an explicit 1/r policy, not a simulated acoustic path.
// Near-field amplification is intentionally suppressed.
func (e Envelope) Gain(distanceMeters float64) (float64,error) {
    if e.Validate()!=nil || !finite(distanceMeters) || distanceMeters<=0 {return 0,ErrInput}
    if e.Curve==Identity {return 1,nil}
    d:=math.Max(distanceMeters,e.MinimumMeters)
    return math.Min(1,e.ReferenceMeters/d),nil
}
// ApplyInterleaved applies a linear amplitude ramp across complete frames.
// Supports mono-derived stereo, 5.1 and 7.1; channel index three is a
// reserved LFE source channel in our canonical export fixtures and must
// remain zero. No in-place output: provenance kept separate.
func ApplyInterleaved(dst,src []float32,channels int,startGain,endGain float64) error {
    if channels!=2 && channels!=6 && channels!=8 {return ErrInput}
    if len(src)==0 || len(src)%channels!=0 || len(src)!=len(dst) {return ErrInput}
    if !finite(startGain)||!finite(endGain)||startGain<0||endGain<0||startGain>1||endGain>1{return ErrInput}
    frames:=len(src)/channels
    if frames==0{return ErrInput}
    for i,x:=range src {
        if !finite(float64(x)) || math.Abs(float64(x))>1{return ErrInput}
        if channels>=6 && i%channels==3 && x!=0{return ErrInput}
    }
    for frame:=0;frame<frames;frame++ {
        t:=0.0
        if frames>1 {t=float64(frame)/float64(frames-1)}
        gain:=startGain+(endGain-startGain)*t
        for ch:=0;ch<channels;ch++ {
            index:=frame*channels+ch
            dst[index]=float32(float64(src[index])*gain)
            if !finite(float64(dst[index])) || math.Abs(float64(dst[index]))>1{return ErrInput}
        }
    }
    return nil
}
