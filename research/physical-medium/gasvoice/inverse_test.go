package gasvoice

import (
 "bytes"
 "testing"
)

// The toy filter depends on c/L. Two different physical parameter vectors
// may be acoustically indistinguishable. This is a MODEL limitation, not
// evidence that real human airway anatomy is equivalent across these states.
func TestInverseNonIdentifiability(t *testing.T) {
 a:=Params{SoundSpeed:340,SourceF0:170,TractLength:0.20,SampleRate:48000,Samples:9600}
 b:=Params{SoundSpeed:680,SourceF0:170,TractLength:0.40,SampleRate:48000,Samples:9600}
 aa,ar,err:=Generate(a);if err!=nil{t.Fatal(err)}
 bb,br,err:=Generate(b);if err!=nil{t.Fatal(err)}
 if ar.FirstResonanceHz!=br.FirstResonanceHz{t.Fatalf("equal c/L should match reference resonances: %.12f %.12f",ar.FirstResonanceHz,br.FirstResonanceHz)}
 if !bytes.Equal(aa,bb){t.Fatal("equivalent c/L unexpectedly generates different surrogate WAV")}
 if ar.SoundSpeedMPS==br.SoundSpeedMPS||a.TractLength==b.TractLength{t.Fatal("negative control used identical parameters")}
}
