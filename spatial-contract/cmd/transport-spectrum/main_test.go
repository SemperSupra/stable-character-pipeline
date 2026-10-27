package main

import (
 "math"
 "testing"
)
func syntheticPair()(a,b []float32){
 a=make([]float32,frames*channels)
 b=make([]float32,frames*channels)
 for frame:=0;frame<frames;frame++{
  waveA:=0.02*math.Sin(2*math.Pi*410*float64(frame)/rate)
  for ch:=0;ch<channels;ch++{
   if ch==3{continue}
   a[frame*channels+ch]=float32(waveA)
   b[frame*channels+ch]=float32(waveA)
   if frame>=gateStart&&frame<gateStop{
    for _,item:=range []struct{buf []float32;offset int}{{a,0},{b,sourceSeek}}{
     x:=float32(0.012*math.Sin(2*math.Pi*690*float64(frame-gateStart+item.offset)/rate))
     item.buf[frame*channels+ch]+=x
    }
   }
  }
 }
 return a,b
}
func TestTransportShiftPreservesAAndMovesBPhase(t *testing.T){
 a,b:=syntheticPair()
 if e:=check(a,b);e!=nil{t.Fatal(e)}
}
func TestTransportFalseAcceptance(t *testing.T){
 a,b:=syntheticPair()
 if e:=check(a,a);e==nil{t.Fatal("identical file incorrectly admitted as seeked transport")}
 for i:=0;i<len(b);i++{b[i]*=0.5}
 if e:=check(a,b);e==nil{t.Fatal("loss of A410 independence undetected")}
}
