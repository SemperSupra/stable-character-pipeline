package medium

import (
    "math"
    "testing"
)

func TestEarthlike(t *testing.T) {
    p,err:=Earthlike().Evaluate();if err!=nil {t.Fatal(err)}
    if p.SoundSpeed<340 || p.SoundSpeed>347 {t.Fatalf("unexpected room-temperature speed %.3f",p.SoundSpeed)}
    f,err:=QuarterWave(1,0.17,p.SoundSpeed);if err!=nil||f<500||f>510 {t.Fatalf("F1 %.3f %v",f,err)}
    if math.Abs(p.Impedance-p.Density*p.SoundSpeed)>1e-9 {t.Fatal("impedance inconsistent")}
}
func TestMixtureShiftResonances(t *testing.T) {
    earth:=Earthlike();other:=Earthlike();other.Species[0].MoleFraction=0.74;other.Species[2].MoleFraction=0.05
    a,e1:=earth.Evaluate();b,e2:=other.Evaluate();if e1!=nil||e2!=nil {t.Fatal(e1,e2)}
    if !(b.SoundSpeed<a.SoundSpeed) {t.Fatal("heavier reference mixture must yield slower sound")}
    f1,_:=QuarterWave(2,0.17,a.SoundSpeed);f2,_:=QuarterWave(2,0.17,b.SoundSpeed)
    if math.Abs(f2/f1-b.SoundSpeed/a.SoundSpeed)>1e-12 {t.Fatal("resonance ratio oracle")}
}
func TestRejectedStates(t *testing.T) {
    cases:=[]State{ {}, {PressurePa:1,TemperatureK:273}, Earthlike(), Earthlike(), Earthlike(), Earthlike(), Earthlike(), Earthlike()}
    cases[2].Species[0].MoleFraction=0.81
    cases[3].Species[0].MoleFraction=math.NaN()
    cases[4].TemperatureK=math.Inf(1)
    cases[5].Species[0].CpMolar=R
    cases[6].Species[0].Name="oxygen"
    cases[7].PressurePa=-1
    for i,c:=range cases {if _,err:=c.Evaluate();err==nil{t.Fatalf("invalid case %d accepted",i)}}
    for _,l:=range []float64{0,-1,math.NaN(),math.Inf(1)} {if _,err:=QuarterWave(1,l,343);err==nil{t.Fatalf("invalid length %v",l)}}
}

func TestQuarterWaveOverflowRejected(t *testing.T) {
 if _,err:=QuarterWave(100,1e-300,math.MaxFloat64);err==nil{t.Fatal("overflow to infinity was accepted")}
}
