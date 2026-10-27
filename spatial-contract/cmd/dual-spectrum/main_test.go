package main

import(
 "math"
 "testing"
)
func synthesized(retuned bool)[]float32{
 data:=make([]float32,frames*nch)
 bHz:=690.0
 if retuned{bHz=930}
 for i:=0;i<frames;i++{
  a:=0.02*math.Sin(2*math.Pi*410*float64(i)/rate)
  b:=0.012*math.Sin(2*math.Pi*bHz*float64(i)/rate)
  data[i*nch]=float32(a+b)
  data[i*nch+1]=float32(a+b)
 }
 return data
}
func TestIndependentSpectralContribution(t *testing.T){
 if err:=verify(synthesized(false),synthesized(true));err!=nil{t.Fatal(err)}
 if err:=verify(synthesized(false),synthesized(false));err==nil{t.Fatal("identical source tone accepted as retune")}
 if err:=verify(make([]float32,frames*nch),synthesized(true));err==nil{t.Fatal("silent source accepted")}
}
