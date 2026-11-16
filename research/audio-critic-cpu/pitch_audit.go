package critic

import (
 "encoding/binary"
 "errors"
 "math"
)

// PitchAudit is an uncalibrated, independent second opinion. It must not be
// interpreted as real speaker anatomy, identity, emotion or clinical evidence.
// EstimatedHz=0 means ABSTAIN. It never trusts the command/source frequency.
type PitchAudit struct {
 Status string `json:"status"`
 EstimatedHz float64 `json:"estimated_f0_hz_if_supported"`
 Candidates []PitchCandidate `json:"candidates"`
 WindowSamples int `json:"window_samples"`
}
type PitchCandidate struct {
 Hertz float64 `json:"hz"`
 Periodicity float64 `json:"periodicity_confidence"`
 FundamentalSupport float64 `json:"spectral_fundamental_support"`
}

// AuditPitchWAV parses WAV with the independent L0 gate and then checks
// local periodicity minima against spectral support at candidate fundamental.
// The threshold/heuristics are deliberately not calibrated; missing-fundamental
// and unresolved octave ambiguity fail closed.
func AuditPitchWAV(wav []byte)(PitchAudit,error){
 var audit PitchAudit
 m,err:=Measure(wav);if err!=nil{return audit,err}
 if m.Silent{return PitchAudit{Status:"silent"},nil}
 if len(wav)<44{return audit,errors.New("short WAV")}
 // Read the final data chunk from a validated file without assuming fixed
 // 44-byte fmt headers. This preserves the existing bounded RIFF parser.
 var payload []byte
 for at:=12;at<len(wav); {
  size:=int(binary.LittleEndian.Uint32(wav[at+4:at+8]))
  if string(wav[at:at+4])=="data"{payload=wav[at+8:at+8+size];break}
  at+=8+size+size%2
 }
 if len(payload)==0{return audit,errors.New("validated WAV lacked data")}
 n:=len(payload)/2
 if n>8192{n=8192}
 if n<1024{return PitchAudit{Status:"insufficient_samples",WindowSamples:n},nil}
 sig:=make([]float64,n)
 var mean,energy float64
 for i:=range sig {
  sig[i]=float64(int16(binary.LittleEndian.Uint16(payload[2*i:2*i+2])))/32768
  mean+=sig[i]
 }
 mean/=float64(n)
 for i:=range sig{sig[i]-=mean;energy+=sig[i]*sig[i]}
 if energy<1e-11{return PitchAudit{Status:"insufficient_energy",WindowSamples:n},nil}
 rate:=float64(m.SampleRate)
 lo:=int(math.Ceil(rate/600));if lo<2{lo=2}
 hi:=int(math.Floor(rate/70));if hi>n/3{hi=n/3}
 if lo>=hi{return PitchAudit{Status:"insufficient_samples",WindowSamples:n},nil}
 diff:=make([]float64,hi+2)
 best:=1.0
 for d:=lo;d<=hi;d++ {
  var squared,base float64
  for i:=0;i<n-d;i++{a,b:=sig[i],sig[i+d];delta:=a-b;squared+=delta*delta;base+=a*a+b*b}
  score:=1.0
  if base>1e-10{score=squared/base}
  diff[d]=score
  if score<best{best=score}
 }
 if best>0.22{return PitchAudit{Status:"nonperiodic",WindowSamples:n},nil}
 // Local minima only, with conservative score proximity to the best.
 candidates:=make([]PitchCandidate,0,8)
 for d:=lo;d<=hi;d++ {
  if diff[d]>best+0.035 || diff[d]>0.20{continue}
  if d>lo && diff[d]>diff[d-1]{continue}
  if d<hi && diff[d]>diff[d+1]{continue}
  f:=rate/float64(d)
  // Direct coherent correlation measures actual source energy at f.
  // A subharmonic period (f/2) caused by an f oscillator has little
  // independent spectral support and must not be labeled f0 by default.
  var re,im float64
  for i,x:=range sig{
   phase:=2*math.Pi*f*float64(i)/rate
   re+=x*math.Cos(phase);im-=x*math.Sin(phase)
  }
  support:=2*math.Hypot(re,im)/math.Sqrt(2*float64(n)*energy)
  if !finiteNonnegative(support){return PitchAudit{},errors.New("nonfinite pitch evidence")}
  if support>1{support=1}
  candidates=append(candidates,PitchCandidate{Hertz:f,Periodicity:math.Max(0,1-diff[d]),FundamentalSupport:support})
 }
 audit=PitchAudit{Status:"unresolved",Candidates:candidates,WindowSamples:n}
 if len(candidates)==0{audit.Status="no_local_period";return audit,nil}
 top,second:=-1.0,-1.0
 topIndex:=0
 for i,c:=range candidates{
  if c.FundamentalSupport>top{second=top;top=c.FundamentalSupport;topIndex=i
  }else if c.FundamentalSupport>second{second=c.FundamentalSupport}
 }
 // No score is a formally calibrated probability; approval is conservative
 // with explicit ambiguity handling. Spectral-energy gaps are mandatory.
 if top<0.20{audit.Status="missing_fundamental_or_ambiguous";return audit,nil}
 if second>0.0 && top<2.5*second{audit.Status="octave_or_harmonic_ambiguous";return audit,nil}
 audit.Status="spectral_supported_uncalibrated"
 audit.EstimatedHz=candidates[topIndex].Hertz
 return audit,nil
}
func finiteNonnegative(x float64)bool{
 return !math.IsNaN(x)&&!math.IsInf(x,0)&&x>=0
}
