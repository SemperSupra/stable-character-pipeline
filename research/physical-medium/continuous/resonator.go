// Package continuous implements a finite-energy, fixed-geometry, first-order
// Thiran fractional-delay toy resonator for source-filter research. This is a
// candidate DSP primitive, NOT the private physicalvocal engine or anatomy.
package continuous

import (
 "crypto/sha256"
 "encoding/binary"
 "errors"
 "fmt"
 "math"
)

const Rate=48000

type Params struct {
 LengthM float64
 SoundSpeedMPS float64
 SourceHz float64
 Samples int
}
type Receipt struct {
 Schema string `json:"schema"`
 WAVSHA256 string `json:"wav_sha256"`
 LengthM float64 `json:"length_m"`
 SoundSpeedMPS float64 `json:"sound_speed_mps"`
 OneWaySamples float64 `json:"one_way_samples"`
 RoundTripSamples float64 `json:"round_trip_samples"`
 FractionalPart float64 `json:"fractional_part"`
 SourceHz float64 `json:"prescribed_source_hz"`
 Peak float64 `json:"peak"`
 SampleRate int `json:"sample_rate_hz"`
 Samples int `json:"samples"`
}

func finitePositive(f float64) bool { return !math.IsNaN(f)&&!math.IsInf(f,0)&&f>0 }

// thiran has N integer samples of delay plus a first-order all-pass that
// contributes a fractional 0<=d<1 group delay at DC. It is immutable once
// constructed. Real-time parameter switching requires a separate, versioned
// crossfade and state migration controller: NEVER mutate delays mid-stream.
type thiran struct {
 ring []float64
 idx int
 coef float64
 prevInput,prevOutput float64
 fractional bool
}
func newThiran(samples float64)(*thiran,error){
 if !finitePositive(samples)||samples<2||samples>4096{return nil,errors.New("unsupported delay")}
 n:=int(math.Floor(samples))
 fraction:=samples-float64(n)
 t:=&thiran{ring:make([]float64,n),fractional:fraction>1e-12}
 if t.fractional {t.coef=(1-fraction)/(1+fraction)}
 if math.IsNaN(t.coef)||math.Abs(t.coef)>=1&&t.fractional{
  return nil,errors.New("unstable fractional delay")
 }
 return t,nil
}
func(t *thiran)step(x float64)float64{
 delayed:=t.ring[t.idx]
 t.ring[t.idx]=x
 t.idx++
 if t.idx==len(t.ring){t.idx=0}
 if !t.fractional{return delayed}
 y:=t.coef*delayed + t.prevInput - t.coef*t.prevOutput
 t.prevInput=delayed
 t.prevOutput=y
 return y
}

// Resonator is a single round-trip acoustic proxy with a causal reflected
// wave and a unit-magnitude Thiran transport, NOT a 9-section tissue model.
type Resonator struct {
 delay *thiran
 previous float64
 feedback float64
}
func NewResonator(length,speed float64)(*Resonator,error){
 if !finitePositive(length)||!finitePositive(speed)||length<0.08||length>0.4||
 speed<100||speed>2000{return nil,errors.New("invalid research resonator geometry/medium")}
 roundTrip:=2*length*Rate/speed
 d,err:=newThiran(roundTrip)
 if err!=nil{return nil,err}
 return &Resonator{delay:d,feedback:-0.65},nil
}
func (r *Resonator)Step(input float64)(float64,error){
 if math.IsNaN(input)||math.IsInf(input,0)||math.Abs(input)>1{return 0,errors.New("invalid excitation")}
 y:=r.delay.step(input+r.feedback*r.previous)
 if math.IsNaN(y)||math.IsInf(y,0){return 0,errors.New("unstable resonator state")}
 r.previous=y
 return 0.28*y,nil
}

// Generate writes an original deterministic 48kHz PCM16 mono synthetic
// vowel-like signal. A prescribed sinusoidal glottal surrogate remains fixed.
// Tiny changes in length or c now change waveform without 1mm integer dead
// zones. This is a demonstration, not scientific tract parameter fitting.
func Generate(p Params)([]byte,Receipt,error){
 var report Receipt
 if !finitePositive(p.LengthM)||!finitePositive(p.SoundSpeedMPS)||!finitePositive(p.SourceHz)||
 p.SourceHz<70||p.SourceHz>600||p.Samples<4800||p.Samples>96000{
  return nil,report,errors.New("invalid bounded synthesis parameters")
 }
 r,err:=NewResonator(p.LengthM,p.SoundSpeedMPS)
 if err!=nil{return nil,report,err}
 wav:=make([]byte,44+2*p.Samples)
 copy(wav[:4],"RIFF")
 binary.LittleEndian.PutUint32(wav[4:8],uint32(len(wav)-8))
 copy(wav[8:12],"WAVE")
 copy(wav[12:16],"fmt ")
 binary.LittleEndian.PutUint32(wav[16:20],16)
 binary.LittleEndian.PutUint16(wav[20:22],1)
 binary.LittleEndian.PutUint16(wav[22:24],1)
 binary.LittleEndian.PutUint32(wav[24:28],Rate)
 binary.LittleEndian.PutUint32(wav[28:32],2*Rate)
 binary.LittleEndian.PutUint16(wav[32:34],2)
 binary.LittleEndian.PutUint16(wav[34:36],16)
 copy(wav[36:40],"data")
 binary.LittleEndian.PutUint32(wav[40:44],uint32(2*p.Samples))
 peak:=0.0
 for i:=0;i<p.Samples;i++{
  t:=float64(i)/Rate
  // Hard-coded synthetic source; no animal/human physiology here.
  source:=0.35*math.Sin(2*math.Pi*p.SourceHz*t)+0.10*math.Sin(4*math.Pi*p.SourceHz*t)
  attack:=math.Min(1,float64(i)/240)
  release:=math.Min(1,float64(p.Samples-1-i)/240)
  sample,err:=r.Step(source*attack*release)
  if err!=nil{return nil,Receipt{},err}
  if math.Abs(sample)>peak{peak=math.Abs(sample)}
  if math.Abs(sample)>=0.99{return nil,Receipt{},errors.New("out of headroom")}
  v:=int16(math.Round(sample*32767))
  binary.LittleEndian.PutUint16(wav[44+2*i:46+2*i],uint16(v))
 }
 roundTrip:=2*p.LengthM*Rate/p.SoundSpeedMPS
 report=Receipt{
  Schema:"research.continuous_resonator.v0",
  WAVSHA256:fmt.Sprintf("%x",sha256.Sum256(wav)),
  LengthM:p.LengthM,SoundSpeedMPS:p.SoundSpeedMPS,
  OneWaySamples:p.LengthM*Rate/p.SoundSpeedMPS,
  RoundTripSamples:roundTrip,
  FractionalPart:roundTrip-math.Floor(roundTrip),
  SourceHz:p.SourceHz,
  Peak:peak,SampleRate:Rate,Samples:p.Samples,
 }
 return wav,report,nil
}
