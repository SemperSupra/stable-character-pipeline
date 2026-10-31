package editable

// Original-only diagnostic Csound orchestration from an immutable public
// score. This deliberately does NOT modify existing Audio Foundry music
// Csound export, imported MIDI or real performer semantics.
import (
 "errors"
 "fmt"
 "strings"
)
func CsoundTempoDiagnostic(p Project,r ScoreRequest)([]byte,error){
 if err:=validRequest(p,r);err!=nil{return nil,err}
 var b strings.Builder
 b.WriteString(`<CsoundSynthesizer>
<CsOptions>
</CsOptions>
<CsInstruments>
sr = 48000
ksmps = 1
nchnls = 1
0dbfs = 1
instr 1
aTone oscili 0.05, cpsmidinn(p4), 1
aClick linseg 0.8, 0.000020833333333, 0, p3-0.000020833333333, 0
out aTone + aClick
endin
</CsInstruments>
<CsScore>
f 1 0 16384 10 1
`)
 for _,n:=range p.Notes{
  start,err:=samplesAt(int64(n.StartTick),r.Tempo,p.Rate);if err!=nil{return nil,err}
  end,err:=samplesAt(int64(n.StartTick+n.LengthTick),r.Tempo,p.Rate);if err!=nil{return nil,err}
  if end<=start{return nil,errors.New("invalid Csound diagnostic interval")}
  fmt.Fprintf(&b,"i 1 %.12f %.12f %d\n",float64(start)/float64(p.Rate),float64(end-start)/float64(p.Rate),n.Pitch)
 }
 total,err:=samplesAt(int64(p.Beats*PPQ),r.Tempo,p.Rate);if err!=nil{return nil,err}
 fmt.Fprintf(&b,"f 0 %.12f\ne\n</CsScore>\n</CsoundSynthesizer>\n",float64(total)/float64(p.Rate))
 return []byte(b.String()),nil
}
