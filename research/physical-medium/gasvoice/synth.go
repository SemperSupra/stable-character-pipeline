// Package gasvoice is a deliberately simplified *acoustic proxy*, not a
// physiological phonation model. A prescribed source F0 excites harmonics
// shaped by a uniform quarter-wave resonator whose c comes from medium.State.
package gasvoice

import (
    "crypto/sha256"
    "encoding/binary"
    "errors"
    "fmt"
    "math"

    medium "github.com/SemperSupra/stable-character-pipeline/research/physical-medium"
)

type Params struct {
    SoundSpeed float64
    SourceF0 float64
    TractLength float64
    SampleRate int
    Samples int
}
type Report struct {
    WAVSHA256 string `json:"wav_sha256"`
    SourceF0Hz float64 `json:"prescribed_source_f0_hz"`
    FirstResonanceHz float64 `json:"uniform_tube_f1_hz"`
    SoundSpeedMPS float64 `json:"sound_speed_mps"`
    SampleRateHz int `json:"sample_rate_hz"`
    Samples int `json:"samples"`
    PeakFraction float64 `json:"generated_peak_fraction"`
}

func valid(x float64) bool { return !math.IsNaN(x) && !math.IsInf(x,0) && x>0 }

// Generate returns a PCM16 mono RIFF/WAVE and a deterministic report.
// The source frequency stays fixed between media; only filter resonances vary.
// The Lorentzian response is a toy spectral-envelope filter, not wave propagation.
func Generate(p Params) ([]byte,Report,error) {
    var r Report
    if !valid(p.SoundSpeed) || !valid(p.SourceF0) || !valid(p.TractLength) ||
       p.SampleRate!=48000 || p.Samples<4800 || p.Samples>96000 ||
       p.SourceF0<70 || p.SourceF0>600 || p.TractLength<0.08 || p.TractLength>0.4 ||
       p.SoundSpeed<100 || p.SoundSpeed>2000 {
        return nil,r,errors.New("out-of-bound research synthesis configuration")
    }
    first,err:=medium.QuarterWave(1,p.TractLength,p.SoundSpeed)
    if err!=nil{return nil,r,err}
    nH:=int(0.48*float64(p.SampleRate)/p.SourceF0)
    if nH>96{nH=96}
    if nH<1{return nil,r,errors.New("insufficient source harmonics")}
    weights:=make([]float64,nH)
    total:=0.0
    for k:=1;k<=nH;k++ {
        f:=float64(k)*p.SourceF0
        envelope:=0.035
        for mode:=1;mode<=4;mode++ {
            center:=float64(2*mode-1)*first
            width:=55.0+0.05*center
            z:=(f-center)/width
            envelope+=1/(1+z*z)
        }
        weights[k-1]=envelope/math.Pow(float64(k),1.05)
        total+=weights[k-1]
    }
    if !valid(total){return nil,r,errors.New("invalid spectral envelope")}
    length:=44+p.Samples*2
    wav:=make([]byte,length)
    copy(wav[:4],"RIFF")
    binary.LittleEndian.PutUint32(wav[4:8],uint32(length-8))
    copy(wav[8:12],"WAVE")
    copy(wav[12:16],"fmt ")
    binary.LittleEndian.PutUint32(wav[16:20],16)
    binary.LittleEndian.PutUint16(wav[20:22],1)
    binary.LittleEndian.PutUint16(wav[22:24],1)
    binary.LittleEndian.PutUint32(wav[24:28],uint32(p.SampleRate))
    binary.LittleEndian.PutUint32(wav[28:32],uint32(p.SampleRate*2))
    binary.LittleEndian.PutUint16(wav[32:34],2)
    binary.LittleEndian.PutUint16(wav[34:36],16)
    copy(wav[36:40],"data")
    binary.LittleEndian.PutUint32(wav[40:44],uint32(p.Samples*2))
    for i:=0;i<p.Samples;i++ {
        time:=float64(i)/float64(p.SampleRate)
        x:=0.0
        for k,w:=range weights {
            x+=w*math.Sin(2*math.Pi*float64(k+1)*p.SourceF0*time)
        }
        // Positive fixed gain, headroom guaranteed by triangle inequality.
        // An attack/release window avoids boundary clicks; no loudness equalizer.
        fade:=math.Min(1,math.Min(float64(i+1),float64(p.Samples-i))/float64(p.SampleRate)*50)
        x=0.80*fade*x/total
        if !math.IsNaN(x) && !math.IsInf(x,0) && math.Abs(x)>r.PeakFraction {
            r.PeakFraction=math.Abs(x)
        }
        if math.IsNaN(x)||math.IsInf(x,0)||math.Abs(x)>=1{return nil,Report{},errors.New("non-finite or clipping output")}
        binary.LittleEndian.PutUint16(wav[44+2*i:46+2*i],uint16(int16(math.Round(x*32767))))
    }
    r.WAVSHA256=fmt.Sprintf("%x",sha256.Sum256(wav))
    r.SoundSpeedMPS=p.SoundSpeed
    r.SourceF0Hz=p.SourceF0
    r.FirstResonanceHz=first
    r.SampleRateHz=p.SampleRate
    r.Samples=p.Samples
    return wav,r,nil
}
