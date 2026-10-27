package main

import "testing"

func valid(profile string,channels int)Receipt {
 energy:=make([]float64,channels);energy[0]=2
 return Receipt{Profile:profile,Channels:channels,SamplesPerChannel:frames,Peak:0.5,ChannelEnergy:energy,WAV:profile+".wav"}
}
func TestAllLayouts(t *testing.T){
 for name,n:=range expected {
  r:=valid(name,n)
  if e:=checkReceipt(r);e!=nil{t.Errorf("%s: %v",name,e)}
 }
}
func TestRejectMalformedOutputs(t *testing.T) {
 items:=[]struct{name string; mutate func(*Receipt)}{
 {"escape",func(r *Receipt){r.WAV="../../secret.wav"}},
 {"wrong channel count",func(r *Receipt){r.Channels=8}},
 {"wrong samples",func(r *Receipt){r.SamplesPerChannel=200}},
 {"silence",func(r *Receipt){r.Peak=0}},
 {"clipping",func(r *Receipt){r.Peak=1.2}},
 {"not finite",func(r *Receipt){r.ChannelEnergy[0]=-0.1}},
 {"all zero",func(r *Receipt){r.ChannelEnergy[0]=0}},
 {"wrong energy vector",func(r *Receipt){r.ChannelEnergy=nil}},
 {"unrecognized profile",func(r *Receipt){r.Profile="thx-spatial-licensed"}},
 }
 for _,item:=range items{t.Run(item.name,func(t *testing.T){
   r:=valid("stereo",2);item.mutate(&r)
   if e:=checkReceipt(r);e==nil{t.Fatal("unsafe or unqualified output admitted")}
 })}
}
