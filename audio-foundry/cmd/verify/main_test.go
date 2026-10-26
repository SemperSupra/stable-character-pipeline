package main

import "testing"

func TestValidate(t *testing.T) {
 var p Probe
 p.Streams = make([]struct { SampleRate string `json:"sample_rate"`; Channels int `json:"channels"` },1)
 p.Streams[0].SampleRate="48000";p.Streams[0].Channels=2
 p.Format.Duration="12.000000"
 if _,err:=validate(p,2000);err!=nil {t.Fatal(err)}
 p.Streams[0].Channels=1
 if _,err:=validate(p,2000);err==nil {t.Fatal("mono must fail")}
 p.Streams[0].Channels=2;p.Format.Duration="6"
 if _,err:=validate(p,2000);err==nil {t.Fatal("short duration must fail")}
 p.Format.Duration="12";if _,err:=validate(p,0);err==nil {t.Fatal("empty wav must fail")}
}
