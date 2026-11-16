// Package preview makes bounded original synthetic demonstrations of airflow
// routing and source categories. It is NOT a validated model of physiological
// respiratory acoustics, voice identity, real instruments, or emotions.
package preview

import (
 "crypto/sha256"
 "encoding/binary"
 "errors"
 "fmt"
 "math"

 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/behavior"
)

const maxSamples = 480000 // 10s @ 48kHz; public-safe fixture cap

type Receipt struct {
 Schema string `json:"schema"`
 ModelValidity string `json:"model_validity"`
 Action behavior.Action `json:"action"`
 SampleRateHz int `json:"sample_rate_hz"`
 Samples int `json:"samples"`
 SHA256 string `json:"wav_sha256"`
 Peak float64 `json:"peak_fraction_full_scale"`
 RMS float64 `json:"rms_fraction_full_scale"`
}
func tone(kind behavior.SourceKind, hz, t, amp float64)float64{
 switch kind {
 case behavior.GlottalVoiced:
  return amp*(0.58*math.Sin(2*math.Pi*hz*t)+0.2*math.Sin(4*math.Pi*hz*t))
 case behavior.GlottalIrregular:
  jitter:=0.02*math.Sin(2*math.Pi*8*t)
  return amp*(0.48*math.Sin(2*math.Pi*(hz*t+jitter))+0.1*math.Sin(4*math.Pi*hz*t))
 case behavior.LipWhistle:
  return amp*0.50*math.Sin(2*math.Pi*hz*t)
 case behavior.EdgeTone:
  return amp*(0.39*math.Sin(2*math.Pi*hz*t)+0.07*math.Sin(4*math.Pi*hz*t))
 case behavior.ReedTone:
  return amp*(0.33*math.Sin(2*math.Pi*hz*t)+0.14*math.Sin(6*math.Pi*hz*t))
 }
 return 0
}
func clamp(x float64)float64 {
 if x>1{return 1}
 if x<0{return 0}
 return x
}
func Render(p behavior.Performance)([]byte,Receipt,error) {
 var report Receipt
 if err:=p.Validate();err!=nil{return nil,report,err}
 samples:=p.Frames[len(p.Frames)-1].EndSample
 if samples<=0||samples>maxSamples{return nil,report,errors.New("synthetic preview beyond bounded sample count")}
 wav:=make([]byte,44+2*samples)
 copy(wav[:4],"RIFF")
 binary.LittleEndian.PutUint32(wav[4:8],uint32(len(wav)-8))
 copy(wav[8:12],"WAVE")
 copy(wav[12:16],"fmt ")
 binary.LittleEndian.PutUint32(wav[16:20],16)
 binary.LittleEndian.PutUint16(wav[20:22],1)
 binary.LittleEndian.PutUint16(wav[22:24],1)
 binary.LittleEndian.PutUint32(wav[24:28],behavior.Rate)
 binary.LittleEndian.PutUint32(wav[28:32],behavior.Rate*2)
 binary.LittleEndian.PutUint16(wav[32:34],2)
 binary.LittleEndian.PutUint16(wav[34:36],16)
 copy(wav[36:40],"data")
 binary.LittleEndian.PutUint32(wav[40:44],uint32(samples*2))
 // Identical deterministic noise stream for all parameter/control A/B.
 // No real recorded voice, breathing or patented acoustic samples.
 rng:=uint32(0x7e351fad)
 var nasalLow,oralLow,portLow float64
 var sumSquares,peak float64
 fi:=0
 for i:=0;i<samples;i++ {
  for i>=p.Frames[fi].EndSample{fi++}
  f:=p.Frames[fi]
  t:=float64(i)/float64(behavior.Rate)
  local:=float64(i-f.StartSample)
  remainder:=float64(f.EndSample-1-i)
  // Soft 5ms frame edges; NOT a realtime interaction smoothing mechanism.
  env:=clamp(local/240)*clamp(remainder/240)
  rng=1664525*rng+1013904223
  white:=2*float64(rng)/4294967296-1
  nasalLow=0.92*nasalLow+0.08*white
  oralLow=0.72*oralLow+0.28*white
  portLow=0.84*portLow+0.16*white
  // Artist-controlled illustrative volume scale, not a human effort or
  // airway diagnostic threshold. Flow is in m3/s and signed.
  flowAmp:=clamp(math.Abs(f.TotalFlowM3S)*3000)
  sample:=0.0
  for _,s:=range f.Sources {
   volume:=s.Amplitude
   switch s.Kind {
   case behavior.AirflowNoise:
    signal:=0.0
    if f.NasalFlowM3S!=0 {signal+=0.28*nasalLow*math.Abs(f.NasalFlowM3S/f.TotalFlowM3S)}
    if f.OralFlowM3S!=0 {signal+=0.22*(white-0.5*oralLow)*math.Abs(f.OralFlowM3S/f.TotalFlowM3S)}
    if f.ObjectFlowM3S!=0 {signal+=0.20*(white-0.5*portLow)*math.Abs(f.ObjectFlowM3S/f.TotalFlowM3S)}
    sample+=volume*flowAmp*signal
   case behavior.GlottalVoiced,behavior.GlottalIrregular,behavior.LipWhistle,behavior.EdgeTone,behavior.ReedTone:
    sample+=flowAmp*tone(s.Kind,s.NominalHz,t,volume)
   case behavior.ArticulatoryClick:
    // An articulatory release need not consume pulmonary airflow.
    // This is an exponentially decaying proxy, not collision FEM.
    age:=local/float64(behavior.Rate)
    sample+=volume*0.45*math.Exp(-age*250)*(white-0.1*oralLow)
   case behavior.ElasticNoise:
    sample+=volume*flowAmp*0.16*(white-portLow)
   }
  }
  sample*=env
  if math.IsNaN(sample)||math.IsInf(sample,0)||math.Abs(sample)>=0.99 {
   return nil,Receipt{},errors.New("invalid finite/headroom synthetic output")
  }
  if abs:=math.Abs(sample);abs>peak{peak=abs}
  sumSquares+=sample*sample
  v:=int16(math.Round(sample*32767))
  binary.LittleEndian.PutUint16(wav[44+2*i:46+2*i],uint16(v))
 }
 report=Receipt{Schema:"respiratory.preview_receipt.v0",ModelValidity:"deterministic_original_synthetic_not_biological",
  Action:p.Action,SampleRateHz:behavior.Rate,Samples:samples,
  SHA256:fmt.Sprintf("%x",sha256.Sum256(wav)),
  Peak:peak,RMS:math.Sqrt(sumSquares/float64(samples))}
 return wav,report,nil
}
