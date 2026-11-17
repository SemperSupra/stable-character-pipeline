// Package observer is an independent, source-blind PCM/WAV signal observer.
// It is intentionally not a diagnosis, perceptual audio metric, respiratory
// physiology estimator, verified F0 recognizer or medical decision system.
package observer
import(
 "encoding/binary"
 "errors"
 "fmt"
 "math"
)

const Rate=48000
const WindowSamples=960 // 20ms
const MaxSamples=480000

type Metrics struct{
 Schema string `json:"schema"`
 Validity string `json:"validity"`
 SampleRateHz int `json:"sample_rate_hz"`
 Samples int `json:"samples"`
 Peak float64 `json:"peak_fraction_full_scale"`
 RMS float64 `json:"rms_fraction_full_scale"`
 Mean float64 `json:"mean_fraction_full_scale"`
 DifferencedEnergyRatio float64 `json:"differenced_energy_ratio"`
 Early20msEnergyFraction float64 `json:"early_20ms_energy_fraction"`
 WindowRMS []float64 `json:"window_rms"`
 Silent bool `json:"silent"`
}
func samples(wav []byte)([]float64,error){
 if len(wav)<44||len(wav)>44+2*MaxSamples||len(wav)%2!=0{return nil,errors.New("WAV too short, too long or odd")}
 if string(wav[:4])!="RIFF"||string(wav[8:12])!="WAVE"||string(wav[12:16])!="fmt "||
  string(wav[36:40])!="data"{return nil,errors.New("noncanonical research WAV layout")}
 if binary.LittleEndian.Uint32(wav[4:8])!=uint32(len(wav)-8)||
  binary.LittleEndian.Uint32(wav[16:20])!=16||
  binary.LittleEndian.Uint16(wav[20:22])!=1||
  binary.LittleEndian.Uint16(wav[22:24])!=1||
  binary.LittleEndian.Uint32(wav[24:28])!=Rate||
  binary.LittleEndian.Uint32(wav[28:32])!=2*Rate||
  binary.LittleEndian.Uint16(wav[32:34])!=2||
  binary.LittleEndian.Uint16(wav[34:36])!=16||
  binary.LittleEndian.Uint32(wav[40:44])!=uint32(len(wav)-44){
  return nil,errors.New("noncanonical 48kHz mono 16-bit PCM/RIFf length")
 }
 n:=(len(wav)-44)/2
 if n<2048||n>MaxSamples{return nil,errors.New("sample count outside analysis limits")}
 out:=make([]float64,n)
 for i:=range out{
  out[i]=float64(int16(binary.LittleEndian.Uint16(wav[44+2*i:46+2*i])))/32768
 }
 return out,nil
}
// AnalyzeWAV computes PCM-only signal features. The first difference energy
// ratio is a crude spectral roughness proxy; it is NOT a calibrated spectral
// centroid or a measurement of actual nose/mouth/anatomy geometry.
func AnalyzeWAV(wav []byte)(Metrics,error){
 x,err:=samples(wav);if err!=nil{return Metrics{},err}
 n:=len(x)
 var sum,squares,difference,peak,early float64
 windows:=make([]float64,0,(n+WindowSamples-1)/WindowSamples)
 for i,v:=range x{
  sum+=v;squares+=v*v
  if a:=math.Abs(v);a>peak{peak=a}
  if i>0{d:=v-x[i-1];difference+=d*d}
  if i<WindowSamples{early+=v*v}
 }
 for i:=0;i<n;i+=WindowSamples{
  end:=i+WindowSamples;if end>n{end=n}
  var energy float64
  for _,v:=range x[i:end]{energy+=v*v}
  windows=append(windows,math.Sqrt(energy/float64(end-i)))
 }
 mean:=sum/float64(n)
 out:=Metrics{Schema:"respiratory.source_blind_pcm_observer.v0",
  Validity:"signal_integrity_and_synthetic_discrimination_not_real_anatomy",
  SampleRateHz:Rate,Samples:n,Peak:peak,RMS:math.Sqrt(squares/float64(n)),
  Mean:mean,WindowRMS:windows,Silent:squares==0}
 if squares>0{
  out.DifferencedEnergyRatio=difference/(4*squares)
  out.Early20msEnergyFraction=early/squares
 }
 vals:=[]float64{out.Peak,out.RMS,out.Mean,out.DifferencedEnergyRatio,out.Early20msEnergyFraction}
 for _,v:=range vals{if math.IsNaN(v)||math.IsInf(v,0){return Metrics{},errors.New("nonfinite audio metric")}}
 if out.Peak>=.999{return Metrics{},errors.New("near-clipped input")}
 return out,nil
}
type ToneEvidence struct{
 Status string `json:"status"`
 TestedFrequencyHz float64 `json:"tested_frequency_hz"`
 EnergyFraction float64 `json:"coherent_line_energy_fraction"`
 WindowSamples int `json:"window_samples"`
}
// EvidenceAt measures the coherent spectral energy at one externally
// specified frequency (not an inferred fundamental) over the first 250 ms.
// Missing-fundamental, doubled-period, breath/noise and pathological
// oscillators can fool single-bin tests; returns evidence, not a voice label.
func EvidenceAt(wav []byte,hz float64)(ToneEvidence,error){
 var out ToneEvidence
 if math.IsNaN(hz)||math.IsInf(hz,0)||hz<70||hz>8000{return out,errors.New("out-of-bounds spectral probe")}
 x,e:=samples(wav);if e!=nil{return out,e}
 n:=len(x);if n>12000{n=12000}
 var mean,energy,real,imag float64
 for _,v:=range x[:n]{mean+=v}
 mean/=float64(n)
 for i,v:=range x[:n]{
  centered:=v-mean
  energy+=centered*centered
  phase:=2*math.Pi*hz*float64(i)/Rate
  real+=centered*math.Cos(phase)
  imag-=centered*math.Sin(phase)
 }
 out=ToneEvidence{Status:"abstain_no_line",TestedFrequencyHz:hz,WindowSamples:n}
 if energy<1e-9{return out,nil}
 fraction:=2*(real*real+imag*imag)/(float64(n)*energy)
 if math.IsNaN(fraction)||math.IsInf(fraction,0){return ToneEvidence{},fmt.Errorf("nonfinite spectral evidence")}
 if fraction<0{fraction=0};if fraction>1{fraction=1}
 out.EnergyFraction=fraction
 // This threshold is an illustrative synthetic candidate gate, not an
 // admitted physical voice fundamental or confidence probability.
 if fraction>=.20{out.Status="coherent_line_present_uncalibrated"}
 return out,nil
}
