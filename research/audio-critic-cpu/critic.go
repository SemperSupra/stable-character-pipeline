// Package critic implements independent deterministic checks of PCM16 mono WAVs.
// Signal integrity metrics do not establish phonetic, perceptual or biological quality.
package critic

import (
 "crypto/sha256"
 "encoding/binary"
 "errors"
 "fmt"
 "math"
)

const MaxBytes = 64 << 20 // 64 MiB bounded fixture; no unbounded allocation.

type Measurement struct {
 SHA256 string `json:"sha256"`
 SampleRate int `json:"sample_rate_hz"`
 Samples int `json:"samples"`
 DurationSeconds float64 `json:"duration_seconds"`
 Peak float64 `json:"peak_fraction_full_scale"`
 RMS float64 `json:"rms_fraction_full_scale"`
 ClippedSamples int `json:"near_clipped_samples"`
 Silent bool `json:"silent"`
 FundamentalHz float64 `json:"f0_hz_if_confident"`
 FundamentalConfidence float64 `json:"f0_periodicity_confidence"`
}

func Measure(buf []byte) (Measurement,error) {
 m:=Measurement{}
 if len(buf)<44 || len(buf)>MaxBytes || string(buf[:4])!="RIFF" || string(buf[8:12])!="WAVE" {return m,errors.New("not a supported bounded RIFF/WAVE")}
 if int64(binary.LittleEndian.Uint32(buf[4:8]))+8!=int64(len(buf)) {return m,errors.New("RIFF length mismatch")}
 var fmtFound,dataFound bool
 var payload []byte
 var channels,bits,format int
 var byteRate,blockAlign,rate uint32
 for at:=12;at<len(buf); {
  if at+8>len(buf) {return m,errors.New("truncated chunk header")}
  name:=string(buf[at:at+4]);size:=int64(binary.LittleEndian.Uint32(buf[at+4:at+8]));at+=8
  if size>int64(len(buf)-at) {return m,errors.New("truncated chunk data")}
  end:=at+int(size)
  switch name {
  case "fmt ":
   if fmtFound || size<16{return m,errors.New("duplicate or short fmt")}
   f:=buf[at:end];format=int(binary.LittleEndian.Uint16(f[0:2]));channels=int(binary.LittleEndian.Uint16(f[2:4]));rate=binary.LittleEndian.Uint32(f[4:8]);byteRate=binary.LittleEndian.Uint32(f[8:12]);blockAlign=uint32(binary.LittleEndian.Uint16(f[12:14]));bits=int(binary.LittleEndian.Uint16(f[14:16]));fmtFound=true
  case "data":
   if dataFound{return m,errors.New("duplicate data")};payload=buf[at:end];dataFound=true
  }
  at=end
  if size%2==1 {if at>=len(buf){return m,errors.New("missing chunk pad")};at++}
 }
 if !fmtFound || !dataFound || format!=1 || channels!=1 || bits!=16 || rate<8000 || rate>192000 || byteRate!=rate*2 || blockAlign!=2 || len(payload)==0 || len(payload)%2!=0 {
  return m,errors.New("unsupported PCM16 mono format or inconsistent header")
 }
 m.SampleRate=int(rate);m.Samples=len(payload)/2;m.DurationSeconds=float64(m.Samples)/float64(rate)
 m.SHA256=fmt.Sprintf("%x",sha256.Sum256(buf))
 var sum float64
 sig:=make([]float64,m.Samples)
 for i:=0;i<m.Samples;i++ {
  x:=float64(int16(binary.LittleEndian.Uint16(payload[i*2:i*2+2])))/32768
  sig[i]=x;mag:=math.Abs(x)
  if mag>m.Peak{m.Peak=mag}
  if mag>=32760.0/32768.0{m.ClippedSamples++}
  sum+=x*x
 }
 m.RMS=math.Sqrt(sum/float64(m.Samples));m.Silent=m.RMS<0.00001
 if !m.Silent {m.FundamentalHz,m.FundamentalConfidence=periodicPitch(sig,m.SampleRate)}
 return m,nil
}

// periodicPitch scores normalized differences, abstaining for nonperiodic clips.
// It is a basic critic diagnostic, not an approved speaker or pitch tracker.
func periodicPitch(sig []float64,rate int) (hz,confidence float64) {
 n:=len(sig);if n>8192{n=8192}
 lo:=rate/600;if lo<2{lo=2};hi:=rate/70;if hi>n/2{hi=n/2}
 if n<256 || lo>=hi{return 0,0}
 best:=1.0;lag:=0
 for d:=lo;d<=hi;d++ {
  var energy,diff float64
  for i:=0;i<n-d;i++ {a,b:=sig[i],sig[i+d];z:=a-b;diff+=z*z;energy+=a*a+b*b}
  if energy>1e-10 {score:=diff/energy;if score<best{best=score;lag=d}}
 }
 confidence=math.Max(0,1-best)
 if lag==0||confidence<0.8{return 0,confidence}
 return float64(rate)/float64(lag),confidence
}
