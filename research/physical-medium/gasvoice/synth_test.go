package gasvoice

import (
 "bytes"
 "encoding/binary"
 "math"
 "testing"

 medium "github.com/SemperSupra/stable-character-pipeline/research/physical-medium"
)

func TestGasAuditionDeterminismAndDistinctMedia(t *testing.T) {
 earth:=medium.Earthlike()
 other:=medium.Earthlike()
 other.Species[0].MoleFraction=0.74
 other.Species[2].MoleFraction=0.05
 a,e:=earth.Evaluate();if e!=nil{t.Fatal(e)}
 b,e:=other.Evaluate();if e!=nil{t.Fatal(e)}
 p:=Params{SoundSpeed:a.SoundSpeed,SourceF0:150,TractLength:0.17,SampleRate:48000,Samples:24000}
 wav,receipt,e:=Generate(p);if e!=nil{t.Fatal(e)}
 again,againReceipt,e:=Generate(p);if e!=nil||!bytes.Equal(wav,again)||againReceipt.WAVSHA256!=receipt.WAVSHA256{t.Fatalf("not deterministic: %v",e)}
 p.SoundSpeed=b.SoundSpeed
 alt,altReceipt,e:=Generate(p);if e!=nil{t.Fatal(e)}
 if bytes.Equal(wav,alt)||receipt.WAVSHA256==altReceipt.WAVSHA256{t.Fatal("medium shift produced identical audio")}
 if receipt.SourceF0Hz!=altReceipt.SourceF0Hz||receipt.FirstResonanceHz<=altReceipt.FirstResonanceHz{t.Fatal("source pitch or resonance invariant broken")}
 if len(wav)!=44+24000*2||binary.LittleEndian.Uint32(wav[24:28])!=48000||string(wav[:4])!="RIFF"{t.Fatal("bad wav header")}
 if receipt.PeakFraction>0.81||receipt.PeakFraction<0.02{t.Fatalf("invalid amplitude %+v",receipt)}
}
func TestInvalidSynthesis(t *testing.T){
 base:=Params{SoundSpeed:343,SourceF0:150,TractLength:0.17,SampleRate:48000,Samples:4800}
 bad:=[]Params{
  {SoundSpeed:math.NaN(),SourceF0:150,TractLength:0.17,SampleRate:48000,Samples:4800},
  {SoundSpeed:math.Inf(1),SourceF0:150,TractLength:0.17,SampleRate:48000,Samples:4800},
  {SoundSpeed:343,SourceF0:0,TractLength:0.17,SampleRate:48000,Samples:4800},
  {SoundSpeed:343,SourceF0:150,TractLength:0,SampleRate:48000,Samples:4800},
  {SoundSpeed:343,SourceF0:150,TractLength:0.17,SampleRate:44100,Samples:4800},
  {SoundSpeed:343,SourceF0:150,TractLength:0.17,SampleRate:48000,Samples:0},
 }
 for i,x:=range bad{if _,_,e:=Generate(x);e==nil{t.Fatalf("invalid case %d accepted",i)}}
 if _,_,e:=Generate(base);e!=nil{t.Fatal(e)}
}
