package continuous

import(
 "bytes"
 "encoding/binary"
 "math"
 "testing"
)
func TestContinuousLengthAndGasSensitivity(t *testing.T){
 baseline:=Params{LengthM:0.170,SoundSpeedMPS:343.22218086816235,SourceHz:160,Samples:9600}
 a,ar,e:=Generate(baseline);if e!=nil{t.Fatal(e)}
 same,sr,e:=Generate(baseline);if e!=nil||!bytes.Equal(a,same)||ar.WAVSHA256!=sr.WAVSHA256{t.Fatal("deterministic replay failed")}
 plus:=baseline;plus.LengthM=0.171
 b,br,e:=Generate(plus);if e!=nil{t.Fatal(e)}
 if bytes.Equal(a,b)||ar.WAVSHA256==br.WAVSHA256{t.Fatal("1mm length step was a dead zone")}
 gas:=baseline;gas.SoundSpeedMPS=341.22131803948224
 c,cr,e:=Generate(gas);if e!=nil{t.Fatal(e)}
 if bytes.Equal(a,c)||ar.WAVSHA256==cr.WAVSHA256{t.Fatal("medium shift was a dead zone")}
 for _,r:=range []Receipt{ar,br,cr}{
  if r.Peak<=0||r.Peak>=0.99||r.SourceHz!=160||r.SampleRate!=48000||r.Samples!=9600{t.Fatalf("invalid generated receipt %+v",r)}
 }
 if len(a)!=19244||string(a[:4])!="RIFF"||binary.LittleEndian.Uint32(a[24:28])!=48000{t.Fatal("invalid PCM16 header")}
}
func TestFractionalAllpassAnalyticPassivityAndDelay(t *testing.T){
 // Strict magnitude unity for a first-order allpass H=(a+z^-1)/(1+a z^-1).
 for _,d:=range []float64{0.03,0.21,0.52,0.79,0.93}{
  line,e:=newThiran(24+d);if e!=nil{t.Fatal(e)}
  a:=line.coef
  if !(a>0&&a<1){t.Fatalf("non-passive pole %.5g",a)}
  got:=(1-a)/(1+a)
  if math.Abs(got-d)>1e-12{t.Fatalf("wrong DC group delay %.12g vs %.12g",got,d)}
  for k:=1;k<=48;k++{
   w:=math.Pi*float64(k)/49
   real:=math.Cos(w);imag:=-math.Sin(w)
   num:=math.Hypot(a+real,imag)
   den:=math.Hypot(1+a*real,a*imag)
   if math.Abs(num/den-1)>1e-12{t.Fatalf("not allpass d=%.3f w=%.3f",d,w)}
  }
  energy:=0.0
  for k:=0;k<4000;k++{
   in:=0.0;if k==0{in=1}
   v:=line.step(in)
   if math.IsNaN(v)||math.IsInf(v,0){t.Fatal("nonfinite impulse")}
   energy+=v*v
  }
  if energy>1.001||energy<0.90{t.Fatalf("impulse allpass energy %.9f",energy)}
 }
}
func TestInvalidAndHighAmplitude(t *testing.T){
 for _,p:=range []Params{
  {LengthM:math.NaN(),SoundSpeedMPS:343,SourceHz:160,Samples:9600},
  {LengthM:0.170,SoundSpeedMPS:math.Inf(1),SourceHz:160,Samples:9600},
  {LengthM:0.170,SoundSpeedMPS:343,SourceHz:0,Samples:9600},
  {LengthM:0.170,SoundSpeedMPS:343,SourceHz:160,Samples:960000},
 }{if _,_,e:=Generate(p);e==nil{t.Fatalf("invalid accepted %+v",p)}}
 r,e:=NewResonator(0.17,343);if e!=nil{t.Fatal(e)}
 if _,e:=r.Step(math.Inf(-1));e==nil{t.Fatal("accepted infinite input")}
}
