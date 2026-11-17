package main
import (
 "testing"
)
func TestSyntheticWAVSignalDecisions(t *testing.T){
 for _,tc:=range []struct{input,want string}{
  {"silence","DIGITAL_SILENCE"},
  {"tone","AUDIO_PRESENT_UNCLASSIFIED"},
  {"breath-like-noise","AUDIO_PRESENT_UNCLASSIFIED"},
  {"clipped","CLIPPED_REJECT"},
 }{
  t.Run(tc.input,func(t *testing.T){
   raw,err:=generate(tc.input);if err!=nil{t.Fatal(err)}
   samples,err:=decode(raw);if err!=nil{t.Fatal(err)}
   got:=inspect(samples)
   if got.Status!=tc.want||got.Samples!=sampleCount{t.Fatalf("bad signal result %+v",got)}
   if tc.input=="tone"||tc.input=="breath-like-noise"{
    if got.RMS<=0||got.Peak<=0||got.ClippedSamples!=0{t.Fatalf("false speech/silence/clip signal %+v",got)}
   }
  })
 }
}
func TestTamperedAndTruncatedAudioReject(t *testing.T){
 raw,err:=generate("truncated");if err!=nil{t.Fatal(err)}
 if _,err=decode(raw);err==nil{t.Fatal("truncated length accepted")}
 raw,err=generate("silence");if err!=nil{t.Fatal(err)}
 raw[22]=2
 if _,err=decode(raw);err==nil{t.Fatal("stereo header accepted")}
 raw,err=generate("silence");if err!=nil{t.Fatal(err)}
 raw[12]='n'
 if _,err=decode(raw);err==nil{t.Fatal("non-PCM fmt accepted")}
 raw,err=generate("silence");if err!=nil{t.Fatal(err)}
 raw[40]=1
 if _,err=decode(raw);err==nil{t.Fatal("incorrect data length accepted")}
}
