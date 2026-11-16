package critic

import (
 "math"
 "math/rand"
 "testing"
)
func TestPitchAuditRecognizesSpectralFundamentalWithoutTrustingSourceCommand(t *testing.T){
 for _,tc:=range []struct{freq float64;harmonics []float64}{
  {160,[]float64{0.5}},
  {160,[]float64{0.30,0.18,0.08}},
  {120,[]float64{0.42,0.12}},
 }{
  sig:=make([]int16,48000)
  for i:=range sig{
   var x float64
   for k,a:=range tc.harmonics{x+=a*math.Sin(2*math.Pi*float64(k+1)*tc.freq*float64(i)/48000)}
   sig[i]=int16(math.Round(x*32000))
  }
  a,err:=AuditPitchWAV(wav(48000,sig));if err!=nil{t.Fatal(err)}
  if a.Status!="spectral_supported_uncalibrated"||math.Abs(a.EstimatedHz-tc.freq)>1.5{
   t.Fatalf("source %.1f: %+v",tc.freq,a)
  }
 }
}
func TestPitchAuditAbstainsWithoutPhysicalTruth(t *testing.T){
 silence:=wav(48000,make([]int16,2400))
 a,e:=AuditPitchWAV(silence);if e!=nil||a.Status!="silent"||a.EstimatedHz!=0{t.Fatalf("silence: %+v %v",a,e)}
 noise:=make([]int16,48000)
 rng:=rand.New(rand.NewSource(42))
 for i:=range noise{noise[i]=int16(rng.Intn(16001)-8000)}
 a,e=AuditPitchWAV(wav(48000,noise))
 if e!=nil||a.EstimatedHz!=0{t.Fatalf("noise falsely certified: %+v %v",a,e)}
 // 320 and 480 Hz harmonics can imply a missing 160 Hz fundamental.
 // Their direct spectrum lacks 160 Hz; abstain rather than hallucinate.
 x:=make([]int16,48000)
 for i:=range x{x[i]=int16(math.Round(8000*math.Sin(2*math.Pi*320*float64(i)/48000)+8000*math.Sin(2*math.Pi*480*float64(i)/48000)))}
 a,e=AuditPitchWAV(wav(48000,x))
 if e!=nil||a.EstimatedHz!=0{t.Fatalf("missing fundamental must abstain: %+v %v",a,e)}
 if _,e=AuditPitchWAV([]byte("bad input"));e==nil{t.Fatal("malformed wav accepted")}
}
