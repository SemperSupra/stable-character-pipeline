package attenuation

import ("math";"testing")
func TestPressureCurve(t *testing.T) {
    e:=Envelope{Curve:InverseDistance,ReferenceMeters:10,MinimumMeters:1}
    ds:=[]float64{1,2,5,10,20,40,100}
    wants:=[]float64{1,1,1,1,.5,.25,.1}
    for i,d:=range ds {
        g,err:=e.Gain(d)
        if err!=nil || math.Abs(g-wants[i])>1e-14 {t.Fatalf("d=%v got %v err %v",d,g,err)}
    }
    e.Curve=Identity
    for _,d:=range ds {
        g,err:=e.Gain(d)
        if err!=nil||g!=1{t.Fatalf("identity d=%v got %v %v",d,g,err)}
    }
}
func TestRejectInvalid(t *testing.T) {
    invalid:=[]float64{0,-1,math.NaN(),math.Inf(1),math.Inf(-1)}
    for _,x:=range invalid {
        _,err:=(Envelope{Curve:InverseDistance,ReferenceMeters:10,MinimumMeters:1}).Gain(x)
        if err==nil{t.Errorf("accepted invalid distance %v",x)}
    }
    for _,e:=range []Envelope{{Curve:InverseDistance,ReferenceMeters:0,MinimumMeters:1},
        {Curve:InverseDistance,ReferenceMeters:10,MinimumMeters:0},
        {Curve:"other",ReferenceMeters:10,MinimumMeters:1},
        {Curve:Identity,ReferenceMeters:math.NaN(),MinimumMeters:1}} {
        if e.Validate()==nil{t.Errorf("accepted invalid envelope %+v",e)}
    }
}
func TestRampsAndFrameBoundaries(t *testing.T) {
    for _,channels:=range []int{2,6,8}{
        src:=make([]float32,2048*channels)
        dst:=make([]float32,len(src))
        for frame:=0;frame<2048;frame++{for ch:=0;ch<channels;ch++{
            if channels>=6 && ch==3{continue}
            src[frame*channels+ch]=0.25
        }}
        if err:=ApplyInterleaved(dst,src,channels,1,.5);err!=nil{t.Fatal(err)}
        for _,frame:=range []int{0,1,255,256,1023,1024,1025,2047}{
            want:=float32(.25*(1-.5*float64(frame)/2047))
            for ch:=0;ch<channels;ch++ {
                got:=dst[frame*channels+ch]
                if channels>=6&&ch==3 {if got!=0 {t.Fatalf("LFE leak %v",got)};continue}
                if math.Abs(float64(got-want))>1e-7 {t.Fatalf("frame %d ch%d gain: %v != %v",frame,ch,got,want)}
            }
        }
    }
}
func TestBadPCMAndChannel(t *testing.T){
    a:=[]float32{.5,.3}
    out:=make([]float32,len(a))
    if ApplyInterleaved(out,a,3,1,1)==nil{t.Fatal("accepted invalid channel")}
    if ApplyInterleaved(out,[]float32{float32(math.NaN()),0},2,1,1)==nil{t.Fatal("accepted NaN")}
    if ApplyInterleaved(out,a,2,-.1,1)==nil{t.Fatal("accepted invalid gain")}
    if ApplyInterleaved(out[:1],a,2,1,1)==nil{t.Fatal("accepted truncated output")}
    b:=make([]float32,6)
    b[3]=.1
    if ApplyInterleaved(b,b,6,1,1)==nil{t.Fatal("accepted unqualified LFE")}
}
