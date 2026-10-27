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

func gatedSource(toneB bool)[]float32 {
 result:=make([]float32,frames*nch)
 for i:=0;i<frames;i++{
  a:=0.02*math.Sin(2*math.Pi*410*float64(i)/rate)
  b:=0.012*math.Sin(2*math.Pi*690*float64(i)/rate)
  if toneB && (i<24575||i>=36865){b=0}
  result[i*nch]=float32(a+b)
  result[i*nch+1]=float32(a+b)
 }
 return result
}
func TestSampleWindowSpectralIsolation(t *testing.T){
 if e:=checkActivity(gatedSource(false),gatedSource(true));e!=nil{t.Fatal(e)}
 if e:=checkActivity(gatedSource(false),gatedSource(false));e==nil{t.Fatal("ungated B accepted")}
 if e:=checkActivity(gatedSource(false),make([]float32,frames*nch));e==nil{t.Fatal("silence admitted")}
}
